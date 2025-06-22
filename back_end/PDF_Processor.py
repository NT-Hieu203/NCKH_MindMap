from PIL import Image
import fitz
import numpy as np
import time
def summary_paragraph(client, paragraph):
    system_prompt = '''
            Bạn là chuyên giao trong việc tóm tắt ngắn gọn các văn bản lịch sử.
            Hãy tóm tắt ngắn gọn đoạn văn được cung cấp nhưng tuyệt đối không được làm mất đi các thông tin lịch sử quan trọng.
            '''
    response = client.chat.completions.create(
            model='gpt-4o-mini',
            temperature=0,

        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": paragraph
            }
            ]
        )
    return response.choices[0].message.content

def extract_key_word(client, summary):
    system_prompt = '''
              Bạn là chuyên gia trong việc trích xuất từ khóa cho thông tin lịch sử.
              Hãy tìm ra một từ/cụm từ khóa có thể thể hiện tổng quát nội dung cốt lõi của đoạn văn.
              YÊU CẦU:
              Chỉ cung cấp từ khóa, không đưa thông tin gì thêm.
              '''
    response = client.chat.completions.create(
            model='gpt-4o-mini',
            temperature=0,

        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": summary
            }
            ]
        )
    return response.choices[0].message.content

def pdf_to_images(documents):
    """
    Chuyển đổi từng trang của file PDF sang định dạng PIL Image.
    Args:
        documents (fitz.Document): Đối tượng PDF.
    Returns:
        list: Một list các dictionary, mỗi dict chứa 'image' (PIL Image)
              và 'page_number' của trang tương ứng.
    """

    doc_images = []
    for page_index, page in enumerate(documents):
        pix = page.get_pixmap(dpi=300)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        doc_images.append({
            "image": img,
            "page_index": page_index,
            "page": page
        })

    return doc_images

def detect_layout(model_detect_layout, pil_image_obj):
    """
    Phát hiện bố cục trên một PIL Image bằng model YOLOv10.
    Args:
        model_detect_layout: Model Doclayout-yolo
        pil_image_obj (PIL.Image.Image): Đối tượng PIL Image của trang.
    Returns:
        ultralytics.engine.results.Results: Đối tượng kết quả từ YOLOv10 predict.
    """

    results = model_detect_layout.predict(
                  pil_image_obj,   # Image to predict
                  imgsz=1024,        # Prediction image size
                  conf=0.3,          # Confidence threshold
                  device="cpu"    # Device to use (e.g., 'cuda:0' or 'cpu')
              )
    return results[0]


def recognize_text_from_image(reader, img_array_or_pil_image):
    """
    Thực hiện OCR trên một hình ảnh (NumPy array hoặc PIL Image) bằng EasyOCR.
    Args:
        reader: easyocr.readers.ImageReader
        img_array_or_pil_image: Hình ảnh dưới dạng NumPy array (OpenCV format) hoặc PIL Image.
    Returns:
        list: Một list các tuple (bbox, text, confidence) từ EasyOCR.
    """
    results = reader.readtext(img_array_or_pil_image, detail=0)
    return results

def recognize_text_from_pymupdf_page(docs, page_index, bbox):
    """
    Trích xuất văn bản từ một trang PyMuPDF trong một vùng (bounding box) nhất định.

    Args:
        docs (fitz.Document): Đối tượng PDF.
        page_index (int): Index của trang trong PDF.
        bbox (list hoặc tuple): Bounding box dưới dạng [x1, y1, x2, y2], đây là tọa độ hình ảnh

    Returns:
        str: Văn bản được trích xuất từ vùng đã cho. Trả về chuỗi rỗng nếu không tìm thấy text.
    """
    try:

        # chuyển sang tọa độ hình ảnh sang tọa độ PDF
        # 300 DPI = 300/72 = 4.167 pixels per point

        scale = 300/72
        # Tạo một fitz.Rect từ bounding box
        x1, y1, x2, y2 = [coord / scale for coord in bbox]

        # Tạo clip rect và trích xuất text
        clip_rect = fitz.Rect(x1, y1, x2, y2)
        pymupdf_page = docs[page_index]
        block = pymupdf_page.get_text('blocks',clip= clip_rect)

        text = block[0][4]
        text = text.replace('.\n','.#')
        text = text.replace('\n',' ')

        return  text

    except Exception as e:
        print(f"  ❌ Lỗi khi trích xuất text từ PyMuPDF: {str(e)}")
        return "" # Trả về chuỗi rỗng nếu có lỗi


def process_pdf_page(docs, model_detect_layout,reader, pdf_page_data, continue_index):
    """
    Xử lý một trang PDF: phát hiện bố cục và nhận dạng văn bản.
    Args:
        model_detect_layout: model Doclayout_yolo
        pdf_page_data (dict): Dictionary chứa 'image' (PIL Image) và 'page_index'.
        continue_index (int): Index tiếp tục từ lần xử lý trước
    Returns:
        tuple: (continue_index, processed_paragraphs, page_results)
    """
    page_index = pdf_page_data["page_index"]
    pil_image = pdf_page_data["image"]

    print(f"\n--- Xử lý trang: {page_index} ---")

    # 1. Phát hiện bố cục
    layout_results = detect_layout(model_detect_layout, pil_image)
    processed_paragraphs = []

    # Kiểm tra xem có boxes không
    if not (hasattr(layout_results, 'boxes') and layout_results.boxes):
        print("    Không tìm thấy đối tượng bố cục nào.")
        return continue_index, processed_paragraphs

    # 2. Xử lý từng box
    for i, box in enumerate(layout_results.boxes):
        bbox = box.xyxy[0].tolist()
        x1, y1, x2, y2 = map(int, bbox)
        label = model_detect_layout.names[int(box.cls[0])]
        score = box.conf[0].item()
        # Chỉ xử lý box không phải abandon
        if label == 'abandon':
            continue
        # Chỉ xử lý box có confidence >= threshold
        if score < 0.4:
            continue

        continue_index += 1

        try:
            # Cắt ảnh theo bbox
            image_cut = pil_image.crop((x1, y1, x2, y2))
            img_np = np.array(image_cut)

            # 4. Nhận dạng văn bản
            start_time = time.time()
            recognized_text_results = recognize_text_from_pymupdf_page(docs, page_index, bbox)
            end_time = time.time()
            print(f"      ⏱️  Thời gian trích text: {end_time - start_time:.2f} giây")
            if recognized_text_results == "":
                recognized_text_results = recognize_text_from_image(reader, img_np)
                recognized_text_results = ' '.join(recognized_text_results)
            print(f"      ✅ Nhận dạng được {recognized_text_results} text")
            # 5. Tạo thông tin paragraph
            if recognized_text_results:
                paragraph_info = {
                    'type': label,
                    'full_text': recognized_text_results,
                    'page_index': page_index,
                    'parent_index': -1,
                    'index': continue_index,
                    'is_title': label == 'title'
                }

                processed_paragraphs.append(paragraph_info)

            else:
                print(f"      ⚠ Không nhận dạng được text")
                continue_index -= 1  # Rollback index nếu không nhận dạng được

        except Exception as e:
            print(f"      ❌ Lỗi khi xử lý box: {str(e)}")
            continue_index -= 1  # Rollback index nếu có lỗi
    e_time = time.time()
    print(f"\n  >>> Hoàn thành xử lý trang {page_index}: {len(processed_paragraphs)} paragraphs")
    return continue_index, processed_paragraphs


def process_full_pdf(model_detect_layout, reader, pdf_path):
    """
    Xử lý toàn bộ file PDF: chuyển đổi, phát hiện bố cục và nhận dạng văn bản từng trang.
    Args:
        pdf_path (str): Đường dẫn đến file PDF.
    Returns:
        dict: Dictionary chứa tất cả kết quả xử lý và thống kê
    """
    print(f"\n🚀 Bắt đầu xử lý PDF: {pdf_path}")
    documents = fitz.open(pdf_path)
    # Chuyển đổi PDF thành ảnh
    start_time = time.time()
    all_page_images = pdf_to_images(documents)
    end_time = time.time()
    total_pages = len(all_page_images)
    print(f"📄 Tổng số trang: {total_pages}")
    print(f"⏱️  Thời gian chuyển đổi: {end_time - start_time:.2f} giây")
    # Khởi tạo kết quả

    all_paragraphs = []
    continue_index = 0

    # Xử lý từng trang
    for i, page_data in enumerate(all_page_images, 1):
        print(f"\n📖 Đang xử lý trang {i}/{total_pages}...")

        try:
            # Xử lý trang và nhận kết quả
            start_time = time.time()
            continue_index, page_paragraphs = process_pdf_page(documents, model_detect_layout,reader, page_data, continue_index)
            end_time = time.time()
            print(f"⏱️  Thời gian detect và trích text trang {i}: {end_time - start_time:.2f} giây")
            # Thêm paragraphs vào danh sách tổng
            all_paragraphs.extend(page_paragraphs)

            print(f"✅ Hoàn thành trang {i}: {len(page_paragraphs)} paragraphs")

        except Exception as e:
            print(f"❌ Lỗi khi xử lý trang {i}: {str(e)}")


    # Tạo thống kê tổng quan
    total_paragraphs = len(all_paragraphs)
    return {
        "pdf_path": pdf_path,
        "total_pages": total_pages,
        "total_paragraphs": total_paragraphs,
        "all_paragraphs": all_paragraphs,
    }

def merge_short_paragraphs(pdf_result_all_paragraphs, n_word=200):
    """
    Gộp các đoạn văn bản ngắn (dưới n_word từ) với đoạn văn bản kế tiếp nó.
    Hàm sẽ thay đổi trực tiếp list đầu vào và giảm số lượng phần tử.

    Args:
        pdf_result_all_paragraphs (list): List các dictionary, mỗi dictionary là một đoạn.
                                          Mỗi dict phải có key 'full_text'.
        n_word (int): Ngưỡng số từ. Nếu đoạn có ít hơn n_word từ, nó sẽ được gộp.

    Returns:
        list: List đã được gộp. Đây cũng chính là list đã được sửa đổi từ đầu vào.
    """
    # Tạo một bản sao để không làm thay đổi list gốc bên ngoài hàm nếu không muốn
    paragraphs = list(pdf_result_all_paragraphs)
    i = 0
    # Dùng 'while' vì độ dài của list sẽ thay đổi trong quá trình lặp
    while i < len(paragraphs) - 1:
        current_paragraph = paragraphs[i]

        # Đếm số từ trong đoạn hiện tại
        word_count = len(current_paragraph.get('full_text', '').split())

        # Nếu đoạn hiện tại ngắn, gộp nó với đoạn kế tiếp
        if word_count < n_word:
            next_paragraph = paragraphs[i + 1]

            # Gộp text của đoạn sau vào đoạn hiện tại
            current_paragraph['full_text'] += " " + next_paragraph.get('full_text', '')

            # Xóa đoạn kế tiếp khỏi list sau khi đã gộp
            paragraphs.pop(i + 1)

            # QUAN TRỌNG: Không tăng 'i'
            # Giữ nguyên 'i' để kiểm tra lại chính đoạn vừa được gộp
            # vì nó có thể vẫn còn ngắn và cần gộp tiếp với đoạn sau nữa.
        else:
            # Nếu đoạn hiện tại đã đủ dài, chuyển sang kiểm tra đoạn tiếp theo
            i += 1

    return paragraphs
