import re
import fitz  # PyMuPDF
from PIL import Image
import io
import base64
import cv2
import numpy as np
from pyzbar.pyzbar import decode  # Barcode reader library
import qrcode

def extract_data_from_election(pdf_path, password=None):
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
            
            # Extract text
            full_text += page.get_text()

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

        # Extract Hindi name
        hindi_name_pattern = re.compile(r'नाव:\s*([\u0900-\u097F\s]+)', re.DOTALL)
        hindi_name_match = hindi_name_pattern.search(full_text)
        if hindi_name_match:
            data['hindi_name'] = hindi_name_match.group(1).strip()
        else:
            data['hindi_name'] = None

        
        # Extract English name
        name_pattern = re.compile(r'Name:\s*([A-Za-z\s]+)', re.IGNORECASE)
        name_match = name_pattern.search(full_text)
        if name_match:
            data['name'] = name_match.group(1).strip()

            # Extract Hindi text including the label
            hindi_name2_pattern = re.compile(
                r'Name:\s*[A-Za-z\s]+\s*(?:\n|\r|\s+)([\u0900-\u097F\s]+:\s*[\u0900-\u097F\s]+)',
                re.DOTALL
            )
            hindi_name2_match = hindi_name2_pattern.search(full_text)
            if hindi_name2_match:
                data['hindi_name2'] = hindi_name2_match.group(1).strip()  # Capture only the Hindi line
            else:
                data['hindi_name2'] = None
            
            # Extract English string after the Hindi name
            english_name_after_hindi_pattern = re.compile(
                rf'{re.escape(data["hindi_name2"])}\s*\n([A-Za-z\s\']+:\s*[A-Za-z\s]+)',
                re.DOTALL
            )
            english_name_after_hindi_match = english_name_after_hindi_pattern.search(full_text)
            if english_name_after_hindi_match:
                data['english_name_after_hindi'] = english_name_after_hindi_match.group(1).strip()
            else:
                data['english_name_after_hindi'] = None

        else:
            data['name'] = None
            data['hindi_name2'] = None
            data['english_name_after_hindi'] = None

            

        # Extract card number
        card_number_match = re.search(r'\b[A-Z]+\d+\b', full_text)
        if card_number_match:
            data['card_number'] = card_number_match.group(0)

        # Extract date of birth directly after "Date of Birth / Age: "
        dob_match = re.search(r'Date of Birth / Age:\s*([\d\-\/\s]+)', full_text)
        if dob_match:
            data['dob'] = dob_match.group(1).strip()
        else:
            data['dob'] = 'Date of Birth not found'

        # Define mappings for English to Hindi gender
        gender_mapping = {
            'Male': 'पुरुष',
            'Female': 'महिला'
        }

        # Extract gender in English
        gender_match = re.search(r'\b(Male|Female)\b', full_text, re.IGNORECASE)
        if gender_match:
            english_gender = gender_match.group(0).capitalize()
            data['gender_english'] = english_gender
            data['gender_hindi'] = gender_mapping.get(english_gender, 'Unknown')

        # Face detection and photo extraction
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        for img_str, image in images:
            open_cv_image = np.array(image.convert('RGB'))
            open_cv_image = open_cv_image[:, :, ::-1].copy()  # Convert to OpenCV format
            gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

            if len(faces) > 0:
                data['profile_photo'] = img_str
                
                # Convert the profile photo to black and white
                black_and_white_image = image.convert("L")  # Convert to grayscale (black and white)
                buffered_bw = io.BytesIO()
                black_and_white_image.save(buffered_bw, format="PNG")
                black_profile_photo_str = base64.b64encode(buffered_bw.getvalue()).decode('utf-8')
                data['black_profile_photo'] = black_profile_photo_str

                break  # Assuming only one profile photo is needed

        # Decode QR code
        for img_str, image in images:
            open_cv_image = np.array(image.convert('RGB'))
            open_cv_image = open_cv_image[:, :, ::-1].copy()
            decoded_objects = decode(open_cv_image)
            for obj in decoded_objects:
                qr_code_data = obj.data.decode('utf-8')
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

    except Exception as e:
        print(f"Error extracting data from PDF: {e}")

    return data
