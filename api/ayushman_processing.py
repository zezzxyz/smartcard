import qrcode  # Import the qrcode library
from datetime import datetime
import re
import fitz  # PyMuPDF
from PIL import Image
import io
import base64
import cv2
import numpy as np
from pyzbar.pyzbar import decode
import pytesseract

def extract_data_from_ayushman(pdf_path, password=None):
    data = {}
    images = []

    try:
        # Open the PDF file
        doc = fitz.open(pdf_path)

        if doc.is_encrypted:
            if password:
                if not doc.authenticate(password):
                    return {'error': 'Wrong password'}
            else:
                return {'error': 'Password required'}

        # Extract text and images from each page
        full_text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Extract text with vertical text handling
            full_text += extract_text_from_page(page)

            # Extract images
            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]

                # Convert image to base64 string
                image = Image.open(io.BytesIO(image_bytes))
                buffered = io.BytesIO()
                image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
                images.append((img_str, image))

        # Face detection and QR code extraction
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        for img_str, image in images:
            open_cv_image = np.array(image.convert('RGB'))
            open_cv_image = open_cv_image[:, :, ::-1].copy()
            gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
            if len(faces) > 0:
                data['profile_photo'] = img_str

            # Decode the largest QR code
            qr_code_data = decode_largest_qr_code(open_cv_image)
            if qr_code_data:
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(qr_code_data)
                qr.make(fit=True)
                qr_img = qr.make_image(fill='black', back_color='white')
                buffered = io.BytesIO()
                qr_img.save(buffered, format="PNG")
                qr_img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
                data['qr_code_image'] = qr_img_str
                break

        # Extract other details
        card_number_matches = re.findall(r'\b[A-Z\d]*\d[A-Z\d]*\b', full_text)
        card_number_matches = [match for match in card_number_matches if len(match) >= 8]
        if card_number_matches:
            data['card_number'] = card_number_matches[0]

        card_number2_match = re.search(r'\b\d{10,20}\b', full_text)
        if card_number2_match:
            data['card_number2'] = card_number2_match.group(0)

        name_match = re.findall(r'\b[A-Za-z]+\s+[A-Za-z]+\s*[A-Za-z]*\b', full_text, re.IGNORECASE)
        for potential_name in name_match:
            if "Enrolment" not in potential_name and "VID" not in potential_name and "DOB" not in potential_name:
                data['name'] = potential_name
                break

        # Extract Hindi name
        hindi_name_pattern = re.compile(r'To\s*\n\s*([\u0900-\u097F\s]+)', re.DOTALL)
        hindi_name_match = hindi_name_pattern.search(full_text)
        data['hindi_name'] = hindi_name_match.group(1).strip() if hindi_name_match else None

        all_capital_words = re.findall(r'\b[A-Z][A-Z\s]+\b', full_text)
        exclude_words = ["NAME", "ENROLMENT", "VID", "DOB", "MALE", "FEMALE"]
        potential_town_district = [word for word in all_capital_words if word not in exclude_words and not re.search(r'\d', word)]
        if potential_town_district:
            data['town'] = potential_town_district[0] if len(potential_town_district) > 0 else None
            data['district'] = potential_town_district[1] if len(potential_town_district) > 1 else None

        vid_match = re.search(r'\bVID\s*:\s*(\d{4}\s\d{4}\s\d{4}\s\d{4})\b', full_text)
        if vid_match:
            data['vid'] = vid_match.group(1).replace(' ', '')

        mobile_match = re.search(r'\bMobile:\s*(\d{10})\b', full_text)
        if mobile_match:
            data['mobile'] = mobile_match.group(1)

        gender_match = re.search(r'\b(M|F)\b', full_text, re.IGNORECASE)
        if gender_match:
            data['gender_english'] = gender_match.group(0).capitalize()

        abha_match = re.search(r'\d{2}-\d{4}-\d{4}-\d{4}', full_text)
        data['abha_number'] = abha_match.group(0) if abha_match else ''

        current_year = datetime.now().year
        previous_year = current_year - 1
        year_match = re.findall(r'\b(19\d{2}|20\d{2}|21\d{2})\b', full_text)
        if year_match:
            extracted_years = [int(year) for year in year_match if int(year) != current_year and int(year) != previous_year]
            if extracted_years:
                data['dob'] = str(extracted_years[0])
            else:
                data['dob'] = None
        else:
            data['dob'] = None

        # Extract Village - make sure you pass 'data' to the extract_village function
        village_found = extract_village(full_text, data)
        data['village'] = village_found

        # Extract Town - ensuring it’s not the same as the village
        town_found = extract_town(full_text, data)
        data['town'] = town_found

        # Extract Town - ensuring it’s not the same as the village
        district_found = extract_district(full_text, data)
        data['town'] = district_found

        

    except Exception as e:
        print(f"Error extracting data from PDF: {e}")

    return data

def extract_text_from_page(page):
    """ Extracts and processes text from a PDF page. Handles vertical text. """
    full_text = ""
    text_blocks = page.get_text("blocks")
    for block in text_blocks:
        block_text = block[4]
        if block[6] != 0:
            block_text = handle_vertical_text(block_text, block[6])
        full_text += block_text + "\n"
    return full_text

def handle_vertical_text(text, rotation):
    """ Adjusts the text based on its rotation to handle vertical text. """
    if rotation == 90 or rotation == 270:
        lines = text.split('\n')
        lines = [line[::-1] for line in lines]
        text = '\n'.join(lines)
    return text

def extract_village(full_text, data):
    # Exclude already known information from the data dictionary
    exclude_list = [
        data.get('name', ''),
        data.get('name_english', ''),
        data.get('card_number', ''),
        data.get('card_number2', ''),
        data.get('abha_number', ''),
        data.get('dob', ''),
        data.get('gender_english', ''),
        "Male", "Female", "Enrolment", "VID", "DOB",
        "Generated", "Card", "Card Generated", "IST", "M", "F"
    ]
    
    # Add month and day names to the exclude list
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    exclude_list.extend(months)
    exclude_list.extend(days)

    # First check if "NOT AVAILABLE" is mentioned
    if "NOT AVAILABLE" in full_text:
        return "NOT AVAILABLE"
    
    # Find all capitalized words or two-word combinations
    potential_villages = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b', full_text)
    
    # Filter out any villages that are in the exclude list
    filtered_villages = [village for village in potential_villages if village not in exclude_list]
    
    # Additional check: remove combinations like "Fri Sep" or any day-month combo
    filtered_villages = [
        village for village in filtered_villages
        if not any(day in village for day in days) and not any(month in village for month in months)
    ]
    
    # Return the first valid village found or "NOT AVAILABLE" if none exist
    return filtered_villages[0] if filtered_villages else "NOT AVAILABLE"


import re

def extract_town(full_text, data):
    # Exclude already known information from the data dictionary
    exclude_list = [
        data.get('name', ''),
        data.get('name_english', ''),
        data.get('card_number', ''),
        data.get('card_number2', ''),
        data.get('abha_number', ''),
        data.get('dob', ''),
        data.get('gender_english', ''),
        "Male", "Female", "Enrolment", "VID", "DOB",
        "Generated", "Card", "Card Generated", "NOT AVAILABLE", "IST", "M", "F"
    ]
    
    # Add the extracted village to the exclude list
    exclude_list.append(data.get('village', ''))

    # Add month and day names to the exclude list
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    exclude_list.extend(months)
    exclude_list.extend(days)

    # Find all capitalized words or two-word combinations
    potential_towns = re.findall(r'\b[A-Z]+(?:\s+[A-Z]+)?\b', full_text)

    # Debug: Print potential towns found
    print(f"Potential towns: {potential_towns}")

    # Normalize exclude_list to lower case for comparison
    normalized_exclude_list = [e.lower() for e in exclude_list]

    # Filter out any towns that are in the exclude list (case insensitive)
    filtered_towns = [town for town in potential_towns if town.lower() not in normalized_exclude_list]

    # Additional check: remove combinations like "Fri Sep" or any day-month combo
    filtered_towns = [
        town for town in filtered_towns
        if not any(day in town for day in days) and not any(month in town for month in months)
    ]
    
    # Debug: Print filtered towns
    print(f"Filtered towns: {filtered_towns}")

    # Return the first valid town found or "NOT AVAILABLE" if none exist
    return filtered_towns[0] if filtered_towns else "NOT AVAILABLE"



def extract_district(full_text, data):
    # Exclude already known information from the data dictionary
    exclude_list = [
        data.get('name', ''),
        data.get('name_english', ''),
        data.get('card_number', ''),
        data.get('card_number2', ''),
        data.get('abha_number', ''),
        data.get('dob', ''),
        data.get('gender_english', ''),
        "Male", "Female", "Enrolment", "VID", "DOB",
        "Generated", "Card", "Card Generated", "NOT AVAILABLE"
    ]
    
    # Add the extracted town and village to the exclude list
    exclude_list.append(data.get('town', ''))
    exclude_list.append(data.get('village', ''))
    
    # Add month and day names to the exclude list
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    exclude_list.extend(months)
    exclude_list.extend(days)

    # Find all capitalized words or two-word combinations
    potential_districts = re.findall(r'\b[A-Z]+(?:\s+[A-Z]+)?\b', full_text)

    # Debug: Print potential districts found
    print(f"Potential districts: {potential_districts}")

    # Normalize exclude_list to lower case for comparison
    normalized_exclude_list = [e.lower() for e in exclude_list]

    # Filter out any districts that are in the exclude list (case insensitive)
    filtered_districts = [district for district in potential_districts if district.lower() not in normalized_exclude_list]

    # Additional check: remove combinations like "Fri Sep" or any day-month combo
    filtered_districts = [
        district for district in filtered_districts
        if not any(day in district for day in days) and not any(month in district for month in months)
    ]
    
    # Debug: Print filtered districts
    print(f"Filtered districts: {filtered_districts}")

    # Return the first valid district found or "NOT AVAILABLE" if none exist
    return filtered_districts[0] if filtered_districts else "NOT AVAILABLE"






def decode_largest_qr_code(image, min_qr_area=1000):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresholded = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    decoded_objects = decode(thresholded)

    if not decoded_objects:
        return None

    largest_qr_data = None
    largest_area = 0

    for obj in decoded_objects:
        qr_area = obj.rect.width * obj.rect.height
        if qr_area > largest_area and qr_area > min_qr_area:
            largest_area = qr_area
            largest_qr_data = obj.data.decode('utf-8')

    return largest_qr_data







