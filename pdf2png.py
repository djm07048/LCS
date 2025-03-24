import os
import fitz  # PyMuPDF
from concurrent.futures import ThreadPoolExecutor

def process_pdf_file(pdf_path, output_dir, dpi=300):
    item_number = os.path.basename(pdf_path).split('_')[0]
    output_filename = f"{item_number}.png"
    output_path = os.path.join(output_dir, output_filename)

    # Open the PDF
    pdf_document = fitz.open(pdf_path)
    page = pdf_document[0]

    # Calculate the new dimensions
    original_width = 110  # mm
    new_width = 170  # mm
    scale_factor = new_width / original_width

    # Convert mm to points (1 mm = 2.83465 points)
    original_width_points = original_width * 2.83465
    new_width_points = new_width * 2.83465

    # Calculate the new height while maintaining the aspect ratio
    original_height_points = page.rect.height
    new_height_points = original_height_points * scale_factor

    # Set the zoom factor based on the new dimensions
    zoom_x = new_width_points / page.rect.width
    zoom_y = new_height_points / page.rect.height

    # Render the page to an image
    mat = fitz.Matrix(zoom_x, zoom_y)
    pix = page.get_pixmap(matrix=mat, dpi=dpi)

    # Save the image as PNG
    pix.save(output_path)

    print(f"Saved {output_filename}")
    # Close the PDF document
    pdf_document.close()

def convert_pdf_to_png(source_path, dpi=300):
    # Create the output directory if it doesn't exist
    output_dir = os.path.join(source_path, 'pngs')
    os.makedirs(output_dir, exist_ok=True)

    # Get a list of all PDF files to process
    pdf_files = [os.path.join(source_path, filename) for filename in os.listdir(source_path) if filename.endswith('_caption.pdf')]

    # Sort the PDF files
    pdf_files.sort()

    # Use a thread pool to process PDF files concurrently
    with ThreadPoolExecutor(max_workers=8) as executor:
        executor.map(lambda pdf_file: process_pdf_file(pdf_file, output_dir, dpi), pdf_files)

def main():
    subject = input("Submit Subject to start the conversion: ")
    source_path = rf"T:\THedu\KiceDB\{subject}"
    convert_pdf_to_png(source_path)

if __name__ == "__main__":
    main()