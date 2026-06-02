'''
对打包好的pdf进行加密
'''
from pikepdf import Pdf, Encryption
import os
import secrets

def encrypt_pdf(input_pdf_path):
    password = secrets.token_urlsafe(8)

    dir_name, original_file_name = os.path.split(input_pdf_path)
    output_file_name = f"{password}_{original_file_name}"
    output_pdf_path = os.path.join(dir_name, output_file_name)

    pdf = Pdf.open(input_pdf_path)

    encryption = Encryption(
        user=password,
        owner=password
    )

    pdf.save(output_pdf_path, encryption=encryption)

    return password, output_pdf_path
