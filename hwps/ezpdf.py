import sys
import win32gui, win32con
import time


def save_pdf_with_text(file_path, interval=1, timeout=3):      #interval을 연장하여 인식 못하고 넘어가는 것 해결
    title = "생성될 PDF 파일의 이름을 입력 해주세요"
    start_time = time.time()

    for _ in range(50):
        dialog_hwnd = win32gui.FindWindow(None, title)

        if dialog_hwnd:
            win32gui.ShowWindow(dialog_hwnd, win32con.SW_HIDE)
            child_hwnds = []
            win32gui.EnumChildWindows(dialog_hwnd, lambda hwnd, param: param.append(hwnd), child_hwnds)

            edit_found = False
            for hwnd in child_hwnds:
                class_name = win32gui.GetClassName(hwnd)
                if class_name == "Edit":
                    win32gui.SendMessage(hwnd, win32con.WM_SETTEXT, None, file_path)
                    edit_found = True
                    break

            if not edit_found:
                print("Edit 컨트롤을 찾을 수 없습니다.")
                return

            for hwnd in child_hwnds:
                text = win32gui.GetWindowText(hwnd)
                if text == "저장(&S)":
                    win32gui.PostMessage(hwnd, win32con.BM_CLICK, 0, 0)
                    break
            break
        else:
            if time.time() - start_time > timeout:
                print(f"타임아웃: 창 '{title}'을(를) 찾을 수 없습니다.")
            time.sleep(interval)
            print(interval, "초만큼 대기합니다.", end="\f")


if __name__ == '__main__':
    save_pdf_with_text(sys.argv[1])  # argv[1] == file_path
