from pikepdf import Pdf, Encryption
import os,random

def encrypt_pdf(input_pdf_path):
    '''
    对打包好的pdf进行加密
    '''
    password = str(random.randint(10000, 99999))

    dir_name, original_file_name = os.path.split(input_pdf_path)
    output_file_name = f"{password}_{original_file_name}"
    output_pdf_path = os.path.join(dir_name, output_file_name)

    pdf = Pdf.open(input_pdf_path)

    encryption = Encryption(
        user=password,  
        owner=password  
    )
    
    pdf.save(output_pdf_path, encryption=encryption)

    try:
        with open(output_pdf_path, 'a', encoding='utf-8') as f:
            f.write(password)
    except Exception as e:
        print(f"无法修改文件 {output_pdf_path}: {e}")

    return password, output_pdf_path
