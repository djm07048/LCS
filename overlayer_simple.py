from modules.overlayer import *
from utils.component import Component


def overlay_component_pdf_onto_base_pdf(base_pdf, base_page_num ,component_pdf, component_page_num, coord):
    base_doc = fitz.open(base_pdf)
    ov = Overlayer(base_doc)
    component_doc = fitz.open(component_pdf)
    ov.pdf_overlay(base_page_num, coord, Component(component_pdf, component_page_num, component_doc.load_page(component_page_num).rect))
    return base_doc


def save_output_pdf(base_doc, output_pdf):
    base_doc.save(output_pdf)


# Example
BASE_PATH = "T:\THedu\Coding\overlayer_simple"
base_pdf = BASE_PATH + r"\base.pdf"
component_pdf = BASE_PATH + r"\component.pdf"

base_doc = overlay_component_pdf_onto_base_pdf(base_pdf, 165, component_pdf, 0, Coord(Ratio.mm_to_px(83.5),Ratio.mm_to_px(87),3))
overlay_component_pdf_onto_base_pdf("base.pdf", 166, "component.pdf", 1, Coord(Ratio.mm_to_px(46),Ratio.mm_to_px(87),3))

base_doc = fitz.open(base_pdf)
ov = Overlayer(base_doc)

component_doc = fitz.open(component_pdf)

ov.pdf_overlay(165, Coord(Ratio.mm_to_px(83.5),Ratio.mm_to_px(87),3), Component(component_pdf, 0, component_doc.load_page(0).rect))
ov.pdf_overlay(166, Coord(Ratio.mm_to_px(46),Ratio.mm_to_px(87),3), Component(component_pdf, 1, component_doc.load_page(1).rect))

base_doc.save(BASE_PATH + r"\output.pdf")