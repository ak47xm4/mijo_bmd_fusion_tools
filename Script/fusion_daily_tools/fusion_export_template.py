# import sys
from pathlib import Path

# mijo 241207 22:10


def create_exr_sequence(comp, output_path):
    """
    創建 EXR 序列輸出節點
    """
    # 創建 Saver 節點
    saver = comp.AddTool("Saver", -32768, -32768)

    # 設置輸出路徑
    saver.Clip = str(output_path)

    # 設置 EXR 格式相關參數
    saver.OpenEXRFormat.Depth = 1
    saver.OpenEXRFormat.Compression = 9
    saver.OpenEXRFormat.DWACompressionLevel = 45.0
    saver.OpenEXRFormat.AlphaEnable = False
    saver.OpenEXRFormat.ZEnable = False
    saver.OpenEXRFormat.CovEnable = False
    saver.OpenEXRFormat.ObjIDEnable = False
    saver.OpenEXRFormat.MatIDEnable = False
    saver.OpenEXRFormat.UEnable = False
    saver.OpenEXRFormat.VEnable = False
    saver.OpenEXRFormat.XNormEnable = False
    saver.OpenEXRFormat.YNormEnable = False
    saver.OpenEXRFormat.ZNormEnable = False
    saver.OpenEXRFormat.XVelEnable = False
    saver.OpenEXRFormat.YVelEnable = False
    saver.OpenEXRFormat.XRevVelEnable = False
    saver.OpenEXRFormat.YRevVelEnable = False
    saver.OpenEXRFormat.XPosEnable = False
    saver.OpenEXRFormat.YPosEnable = False
    saver.OpenEXRFormat.ZPosEnable = False
    saver.OpenEXRFormat.XDispEnable = False
    saver.OpenEXRFormat.YDispEnable = False

    print(f"已創建 EXR 輸出節點，路徑: {output_path}")
    return saver


def create_prores_mov(comp, output_path):
    """
    創建 ProRes 422 MOV 輸出節點
    """
    # 創建 Saver 節點
    saver = comp.AddTool("Saver", -32768, -32768)

    # 設置輸出路徑
    saver.Clip = str(output_path)

    # 設置 ProRes 422 格式相關參數
    saver.OutputFormat = "QuickTimeMovies"
    saver.QuickTimeMovies.Compression = "Apple ProRes 422_apcn"
    saver.SetAttrs({"TOOLB_PassThrough": True})
    print(f"已創建 ProRes MOV 輸出節點，路徑: {output_path}")
    return saver


def create_jpeg_sequence(comp, output_path):
    """
    創建 JPEG 序列輸出節點
    """
    # 創建 Saver 節點
    saver = comp.AddTool("Saver", -32768, -32768)

    # 設置輸出路徑
    saver.Clip = str(output_path)

    # 設置 JPEG 格式相關參數
    saver.OutputFormat = "JpegFormat"
    saver.JpegFormat.Quality = 97
    saver.JpegFormat.ChromaSubsampling = 1

    print(f"已創建 JPEG 序列輸出節點，路徑: {output_path}")
    return saver


def main():

    # 獲取當前 Fusion 合成
    fusion = bmd.scriptapp("Fusion")
    comp = fusion.GetCurrentComp()

    if not comp:
        print("錯誤：請先打開一個合成")
        return

    # 獲取當前合成檔案路徑
    comp_path = Path(comp.GetAttrs()['COMPS_FileName'])
    comp_path_list = str(comp_path).split("\\")
    # 解析路徑結構
    shot_name = comp_path.stem  # 獲取檔案名稱（不含副檔名）

    print(f"合成檔案路徑: {comp_path}")
    print(f"鏡頭名稱: {shot_name}")

    # 創建輸出目錄
    exr_output_path = comp_path.parent / "output" / shot_name / shot_name[:-11]
    exr_output_path = str(exr_output_path) + ".0000.exr"
    mov_output_path = comp_path.parent / shot_name
    mov_output_path = str(mov_output_path) + '.mov'
    jpeg_output_path = comp_path.parent / "output" / shot_name / "jpg" / shot_name[:
                                                                                   -11]
    jpeg_output_path = str(jpeg_output_path) + ".0000.jpg"

    try:
        # 創建輸出節點
        jpeg_saver = create_jpeg_sequence(comp, jpeg_output_path)
        exr_saver = create_exr_sequence(comp, exr_output_path)
        mov_saver = create_prores_mov(comp, mov_output_path)

    except Exception as e:
        print(f"錯誤：{str(e)}")


if __name__ == "__main__":
    comp.Lock()
    main()
    comp.Unlock()
