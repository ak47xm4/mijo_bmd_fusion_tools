import csv
from pathlib import Path


def create_animated_transform(comp, csv_path):
    """
    從CSV檔案創建帶有動畫的Transform節點
    """
    # 創建 Transform 節點
    transform = comp.AddTool("Transform", -32768, -32768)

    # 调试信息
    if transform is None:
        print("錯誤：Transform 節點未能創建")
        return None

    print(f"Transform 節點創建成功: {transform}")

    # 確保 Center 屬性存在
    if not hasattr(transform, 'Center'):
        print("錯誤：Transform 節點缺少 Center 屬性")
        return None

    # 讀取CSV檔案
    with open(csv_path, 'r') as file:
        csv_reader = csv.DictReader(file)
        data = list(csv_reader)

    # 獲取時間範圍
    start_frame = int(data[0]['frame'])
    end_frame = int(data[-1]['frame'])

    transform.Center = comp.XYPath()

    # 設置關鍵幀
    for row in data:
        frame = int(row['frame'])
        x = float(row['shift_x'])
        y = float(row['shift_y'])

        try:
            # 設置值
            transform.Center[frame] = (x, y)
            # 明確設置關鍵幀
            # transform.Center.SetKeyFrameAtTime(frame)
        except Exception as e:
            print(f"設置關鍵幀時發生錯誤：{str(e)}")
            return None

    print(f"已創建Transform節點，並設置了從第{start_frame}幀到第{end_frame}幀的動畫")
    return transform


def main():
    comp = None
    # try:
    print(f"Fusion 对象: {fusion}")  # 调试信息
    comp = fusion.GetCurrentComp()

    if not comp:
        print("錯誤：請先打開一個合成")
        return

    # 使用文件对话框选择CSV文件
    csv_path = fusion.RequestFile(
        "選擇CSV檔案", "CSV Files (*.csv)|*.csv|All Files (*.*)|*.*", False)
    print(csv_path)

    if not csv_path:
        print("未選擇CSV檔案")
        return

    if not Path(csv_path).exists():
        print(f"錯誤：找不到CSV檔案：{csv_path}")
        return

    comp.Lock()
    transform = create_animated_transform(comp, csv_path)
    comp.Unlock()

    print("完成!")

    # except Exception as e:
    #     print(f"錯誤：{str(e)}")
    #     if comp:
    #         comp.Unlock()


if __name__ == "__main__":
    main()
