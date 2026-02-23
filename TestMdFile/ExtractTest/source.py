import fitz  # PyMuPDF
import os

pdf_path = "c:\\Users\\priya\\Downloads\\selfstudys_com_file.pdf"

output_image_dir = "C:\\Users\\priya\\Desktop\\0125_Android\\TestMdFile\\Result"

output_md_path = "C:\\Users\\priya\\Desktop\\0125_Android\\TestMdFile\\Result\\textbook.md"

def extract_text_and_images(pdf_path, output_image_dir):

        # Create the output directory for images
        os.makedirs(output_image_dir, exist_ok=True)

        # Open the PDF file
        doc = fitz.open(pdf_path)
        text = ""
        image_count = 0

        # Iterate through each page
        for page_num in range(len(doc)):
                page = doc.load_page(page_num)

                # Extract text
                text += page.get_text("text") + "\n\n"

                # Extract images
                image_list = page.get_images(full=True)
                for img in image_list:
                        xref = img[0]  # Image reference number
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]

                        # Save the image
                        image_path = os.path.join(output_image_dir, f"image_{image_count}.{base_image['ext']}")
                        image_name = image_path.split("\\")[-1]


                        with open(image_path, "wb") as image_file:
                                image_file.write(image_bytes)

                        # Add image reference to the text
                        text += f"![Image {image_count}]({image_name})\n\n"
                        image_count += 1
        
        with open(output_md_path, "w", encoding="utf-8") as file:
                file.write(text)


extract_text_and_images(pdf_path, output_image_dir)
# print(text_with_images)