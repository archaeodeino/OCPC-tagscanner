from PIL import Image
from spellchecker import SpellChecker
import os, re, pytesseract

#Below is the command to run a new training session via tesstrain
#make training MODEL_NAME=OCPC START_MODEL=eng TESSDATA=../tessdata/ MAX_ITERATIONS=2000

spell = SpellChecker()

def extract_text_from_image(image):
    text = pytesseract.image_to_string(image, lang='eng', config= f'--psm 3 -c tessedit_char_whitelist=0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ,;-')
    #try psm 11?
    #enable the line below for debugging
    #print(text)
    return text

def get_accession(text):
    start_index = find_next_number(text)
    if "Loc" in text:
        end_index = text.find("Loc")
    else:
        end_index = text.find("PC") + 6
    return text[start_index : end_index]

def get_locality(text):
    start_index = find_next_number(text, text.find("Loc"))
    end_index = text.find("Sp")
    return text[start_index: end_index]

def get_specimen(text):
    start_index = find_next_number(text, text.find("Spec"))
    return text[start_index:]

def get_element(text):
    end_index = text.find(",")
    word = text[: end_index].replace(' ', '')
    return "".join(filter(str.isalpha, word))

def get_portion(text):
    start_index = text.find(",")
    end_index = text.find(";")
    word = text[start_index + 2 : end_index]
    word = "".join(filter(str.isalpha, word))
    if spell.correction(word) and word != spell.correction(word):
        return spell.correction(word)
    else:
        return word

def find_next_number(text, start=0):
    #returns the next index of a number
    pattern = r'\d+'
    match = re.search(pattern, text[start:])
    if match:
        return match.start() + start
    return None

def find_next_letter(text, start_index=0):
    #returns the next index of a letter
    for i in range(len(text[start_index:])):
        if text[i].isalpha():
            return i + start_index
    return None

def find_next_space(text, start_index=0):
    #returns index of the next space
    for i in range(len(text[start_index:])):
        if text[i].isspace():
            return i + start_index
    return None

def clean_accession(text):
    #cleans out extra characters
    text = text.replace(' ', '')
    text = text.replace('', '')
    text = text.replace('.', '')
    #print(text)
    return text


def text_to_dict(text):
    #Step One, split the text into a list for each new line 
    og_list = text.splitlines()
    #remove any empty lines
    list_of_text =  [item for item in og_list if (item and len(item)>5)]
    #print(list_of_text)

    #step 2. get the start index
    i=0
    acc= "None"
    can_process = False
    for line in list_of_text:
        if "Acc" in line:
            acc = clean_accession(line)
        if "ORANGE" in line:
            can_process = True
        elif not can_process:
            i += 1

    #Step 3, grab the data we actually need from the strings
    if can_process:
        image_dict = {
            "Accession": get_accession(acc),
            "Locality": get_locality(acc),
            "Specimen": get_specimen(acc),
            "Taxon": list_of_text[i + 2].replace(' ', ''),
            "Element": get_element(list_of_text[i + 3]),
            "Portion": get_portion(list_of_text[i + 3])
        }
        return(image_dict)
    return

script_dir = os.path.dirname(__file__)
input_path = os.path.join(script_dir, "input")
output_path = os.path.join(script_dir, "output")
png_path = os.path.join(script_dir, "converted_pngs")
error_path = os.path.join(script_dir, "unreadable")

for filename in os.listdir(input_path):
    full_path = os.path.join(input_path, filename)
    #check for jpgs
    print(filename)
    if "JPG" in filename:
        old_img = Image.open(full_path)
        new_name = filename.replace("JPG", "png")
        new_path = os.path.join(png_path, (new_name))
        flipped_img = old_img.transpose(Image.FLIP_TOP_BOTTOM)
        flip_again = flipped_img.transpose(Image.FLIP_LEFT_RIGHT)
        flip_again.save(new_path)
        full_path = os.path.join(png_path, new_name)

    #cleaning image for processing: convert to grayscale and apply threshold
    color_img = Image.open(full_path)
    gray_img = color_img.convert('L')
    threshold = 128
    binary_img = gray_img.point(lambda p: 255 if p > threshold else 0)

    fossil_info = text_to_dict(extract_text_from_image(binary_img))

    #enable the following line for debugging
    print(fossil_info) 

    # OCPC [#SPEC] [taxon name] [element] [portion]
    if fossil_info is not None:
        new_name = "OCPC_" + fossil_info["Specimen"] + "_" + fossil_info["Taxon"] + "_" + fossil_info["Element"] + "_" + fossil_info["Portion"] + ".png"
        #just in case any weird characters slipped through
        new_name = new_name.replace(' ', '')
        new_name = new_name.replace('|', '')
        new_name = new_name.replace('+', '')
        new_name = new_name.replace(':', '')
        new_path = os.path.join(output_path, (new_name))
    else:
        if not new_name:
            new_name = filename
        new_path = os.path.join(error_path, (new_name))

    #enable the following line for debugging
    #print(new_path)
    image = Image.open(full_path)
    image.save(new_path)

