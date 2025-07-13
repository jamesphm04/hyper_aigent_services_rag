import fitz
import matplotlib.patches as patches
import matplotlib.pyplot as plt
from PIL import Image

def plot_pdf_with_boxes(pdf_page, segments):
    pix = pdf_page.get_pixmap()
    pil_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    fig, ax = plt.subplots(1, figsize=(10, 10))
    ax.imshow(pil_image)
    categories = set()
    category_to_color = {
        "Formula": "gold",
        "FigureCaption": "mediumslateblue",
        "NarrativeText": "deepskyblue",
        "ListItem": "dodgerblue",
        "Title": "orchid",
        "Address": "saddlebrown",
        "EmailAddress": "darkorange",
        "Image": "forestgreen", 
        "PageBreak": "gray",
        "Table": "tomato",
        "Header": "slategray",
        "Footer": "lightgray",
        "CodeSnippet": "darkred",
        "PageNumber": "black",
        "UncategorizedText": "lightsteelblue",
    }
    for segment in segments:
        points = segment["coordinates"]["points"]
        layout_width = segment["coordinates"]["layout_width"]
        layout_height = segment["coordinates"]["layout_height"]
        scaled_points = [
            (x * pix.width / layout_width, y * pix.height / layout_height)
            for x, y in points
        ]
        box_color = category_to_color.get(segment["type"], "deepskyblue")
        categories.add(segment["type"])
        rect = patches.Polygon(
            scaled_points, linewidth=1, edgecolor=box_color, facecolor="none"
        )
        ax.add_patch(rect)

    # Make legend
    legend_handles = [patches.Patch(color="deepskyblue", label="Text")]
    for category in ["Formula", "FigureCaption", "NarrativeText", "ListItem", "Title",
                     "Address", "EmailAddress", "Image", "PageBreak", "Table",
                     "Header", "Footer", "CodeSnippet", "PageNumber", "UncategorizedText"]:
        if category in categories:
            legend_handles.append(
                patches.Patch(color=category_to_color[category], label=category)
            )
    ax.axis("off")
    ax.legend(handles=legend_handles, loc="upper right")
    plt.tight_layout()
    plt.show()


def render_page(file_id, doc_list: list, page_number: int, print_text=True) -> None:
    file_path = f"downloads/{file_id}.pdf"
    
    pdf_page = fitz.open(file_path).load_page(page_number - 1)
    page_docs = [
        doc for doc in doc_list if doc.metadata.get("page_number") == page_number
    ]
    segments = [doc.metadata for doc in page_docs]
    plot_pdf_with_boxes(pdf_page, segments)
    if print_text:
        for doc in page_docs:
            print(f"{doc.page_content}\n")
            