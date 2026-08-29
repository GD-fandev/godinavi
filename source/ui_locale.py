import ctypes
import json
from pathlib import Path


LANGUAGE_LABELS = {"ko": "한국어", "ja": "日本語", "en": "English"}
CURRENT_LANGUAGE = "ko"

TRANSLATIONS = {
    "ja": {
        "GodiNavi 좌표 매핑 도구": "GodiNavi 座標マッピングツール",
        "맵 이미지 불러오기": "マップ画像を開く",
        "현재 이미지 교체": "現在の画像を差し替え",
        "저장된 맵 불러오기": "保存済みマップを開く",
        "맵 이름 일괄 편집": "マップ名の一括編集",
        "월드맵 위치 편집": "ワールドマップ位置編集",
        "월드맵 px": "ワールドマップ px",
        "1. 월드맵에서 위치 클릭\n2. 목록에서 맵 선택\n3. 선택 맵 연결 버튼": "1. ワールドマップ上の位置をクリック\n2. リストからマップを選択\n3. 選択マップを関連付け",
        "선택 맵 연결": "選択マップを関連付け",
        "연결 삭제": "関連付けを削除",
        "연결할 맵을 선택해 주세요.": "関連付けるマップを選択してください。",
        "월드맵에서 위치를 먼저 클릭해 주세요.": "先にワールドマップ上の位置をクリックしてください。",
        "연결을 삭제할 맵을 선택해 주세요.": "関連付けを削除するマップを選択してください。",
        "월드맵 이미지를 찾을 수 없습니다.\n{path}": "ワールドマップ画像が見つかりません。\n{path}",
        "작업자료 합치기": "作業データを統合",
        "현재 맵 저장": "現在のマップを保存",
        "맵 정보": "マップ情報",
        "한국어": "韓国語",
        "일본어": "日本語",
        "영어": "英語",
        "+ 패턴 추가": "+ パターン追加",
        "기준점": "基準点",
        "이미지에서 위치를 클릭한 뒤 게임 X:Y를 입력하세요.": "画像上の位置をクリックして、ゲーム内のX:Yを入力してください。",
        "빈 곳 클릭: 기준점 추가 · 점 클릭: 선택\nCtrl+좌드래그: 점 이동 · Ctrl+휠: 확대/축소\n우클릭 드래그: 화면 이동 · 분산된 기준점 4개 이상 권장": "空白をクリック：基準点を追加・点をクリック：選択\nCtrl+左ドラッグ：点を移動・Ctrl+ホイール：拡大/縮小\n右ドラッグ：画面を移動・分散した基準点を4点以上推奨",
        "검증 오차": "検証誤差",
        "뚜렷한 이상 기준점 없음": "明確な異常基準点なし",
        "확인 필요: 기준점 #{number} · 검증 오차 {error:.1f}px": "要確認：基準点 #{number}・検証誤差 {error:.1f}px",
        "기준점 {count}개\n평균 오차 {rmse:.2f}px · 최대 {maximum:.2f}px\n{suspect}": "基準点 {count}個\n平均誤差 {rmse:.2f}px・最大 {maximum:.2f}px\n{suspect}",
        "최소 3점, 권장 4~6점입니다.": "最低3点、4～6点を推奨します。",
        "게임 X:Y": "ゲーム X:Y",
        "이미지 px": "画像 px",
        "선택점 삭제": "選択点を削除",
        "게임 좌표 편집": "ゲーム座標を編集",
        "편집할 기준점을 선택해 주세요.": "編集する基準点を選択してください。",
        "전체 삭제": "すべて削除",
        "계산 전": "計算前",
        "계산 가능": "計算可能",
        "좌표 변환 계산": "座標変換を計算",
        "예상 위치 찾기": "推定位置を検索",
        "위치 추측 불가": "位置を推定できません",
        "위치 추측을 위해 기준점을 하나 이상 입력해 주세요.": "位置を推定するには、基準点を1つ以上入力してください。",
        "찾을 게임 좌표를 X:Y 형식으로 입력해 주세요.": "検索するゲーム座標をX:Y形式で入力してください。",
        "위치 추측에 사용할 측량 완료 지도가 없습니다.": "位置推定に使用できる測量済みマップがありません。",
        "같은 지역의 측량 자료": "同じ地域の測量データ",
        "전체 측량 자료": "全測量データ",
        "예상 위치 X:Y {x}:{y}\n{source} {count}개 기준 · 노란 영역은 추측 범위": "推定位置 X:Y {x}:{y}\n{source} {count}件を参照・黄色い範囲は推定領域",
        "맵 이미지를 불러오세요": "マップ画像を開いてください",
        "게임 좌표 입력": "ゲーム座標の入力",
        "이미지 위치": "画像位置",
        "게임 X": "ゲーム X",
        "게임 Y": "ゲーム Y",
        "입력 확인": "入力確認",
        "X와 Y는 정수로 입력해 주세요.": "XとYは整数で入力してください。",
        "저장된 맵 선택": "保存済みマップを選択",
        "한국어 이름": "韓国語名",
        "일본어 이름": "日本語名",
        "영어 이름": "英語名",
        "기준점 수": "基準点数",
        "이미지": "画像",
        "선택 맵 삭제": "選択マップを削除",
        "불러오기": "開く",
        "등록된 맵": "登録済みマップ",
        "대표 이름": "代表名",
        "맵 ID": "マップID",
        "언어별 이름 패턴": "言語別の名前パターン",
        "자동 예측": "自動予測",
        "자동 예측 완료": "自動予測完了",
        "자동 예측 불가": "自動予測できません",
        "자동 예측의 기준이 될 맵을 선택해 주세요.": "自動予測の基準にするマップを選択してください。",
        "선택한 맵의 이미지 파일명에서 층 번호를 찾을 수 없습니다.": "選択したマップの画像ファイル名から階番号を検出できません。",
        "같은 파일명 형식의 다른 번호 이미지를 찾지 못했습니다.": "同じファイル名形式の別番号画像が見つかりません。",
        "예측할 연속 이미지가 없거나 입력한 이름에서 현재 층 번호를 찾지 못했습니다.": "予測対象の連番画像がないか、入力した名前から現在の階番号を検出できません。",
        "연속된 이미지의 맵 이름 {count}개를 자동으로 채웠습니다.\n내용을 확인한 뒤 전체 이름 저장을 눌러 주세요.": "連番画像のマップ名を{count}件自動入力しました。\n内容を確認してから「すべての名前を保存」を押してください。",
        "한 줄에 패턴 하나를 입력합니다. 첫 번째 줄이 대표 이름입니다.": "1行につき1パターンを入力します。先頭行が代表名です。",
        "영문·숫자·밑줄(_)·하이픈(-)만 사용": "英数字・アンダースコア(_)・ハイフン(-)のみ使用可能",
        "취소": "キャンセル",
        "전체 이름 저장": "すべての名前を保存",
        "저장 완료": "保存完了",
        "삭제 완료": "削除完了",
        "저장 불가": "保存できません",
        "한국어·일본어·영어 중 한 언어 이상의 맵 이름을 입력해 주세요.": "韓国語・日本語・英語のうち、少なくとも1つの言語でマップ名を入力してください。",
        "선택 필요": "選択が必要です",
        "이미지 없음": "画像がありません",
        "이미지 오류": "画像エラー",
        "데이터 오류": "データエラー",
        "합치기 완료": "統合完了",
        "합치기 실패": "統合失敗",
        "동일한 맵 ID 발견": "同じマップIDが見つかりました",
        "맵 ID 확인": "マップIDを確認",
        "맵 ID 중복": "マップIDが重複しています",
        "추가": "追加",
        "교체": "置換",
        "유지": "維持",
        "기존 자료 유지": "既存データを維持",
        "전체 합치기 중단": "統合を中止",
        "맵별 파일은 다음 폴더에 저장됩니다.": "マップ別ファイルは次のフォルダーに保存されます。",
        "맵 이미지 선택": "マップ画像を選択",
        "연속 이미지 일괄 등록": "連番画像の一括登録",
        "같은 폴더에서 번호가 이어지는 이미지 {count}개를 찾았습니다.\n\n다른 이미지도 함께 사전 저장하시겠습니까?\n맵 이름과 파일명의 번호를 대응하여 자동으로 개별 맵 데이터를 생성합니다.\n나머지 이미지의 기준점은 비어 있는 상태로 저장됩니다.": "同じフォルダーで連番画像を{count}件見つけました。\n\n他の画像もまとめて事前登録しますか？\nマップ名とファイル名の番号を対応させ、個別のマップデータを自動生成します。\n残りの画像の基準点は空の状態で保存されます。",
        "{count}개 맵 데이터를 각각 저장했습니다.\n나머지 이미지의 기준점은 비어 있습니다.": "{count}件のマップデータを個別に保存しました。\n残りの画像の基準点は空です。",
        "교체할 맵 이미지 선택": "差し替えるマップ画像を選択",
        "대체할 맵 이미지 선택": "代替マップ画像を選択",
        "합칠 맵 작업자료 선택": "統合するマップデータを選択",
        "맵 JSON": "マップJSON",
        "모든 파일": "すべてのファイル",
        "평균 오차": "平均誤差",
        "최대": "最大",
        "개 더 필요": "点追加が必要",
        "개": "点",
        "기준점이 최소 4개 필요합니다.": "基準点が最低4点必要です。",
        "기준점이 한 직선에 몰려 있습니다. 서로 다른 방향으로 퍼진 점을 지정해 주세요.": "基準点が一直線上にあります。異なる方向に離れた点を指定してください。",
        "언어 설정": "表示言語",
        "언어 변경은 프로그램을 다시 실행하면 적용됩니다.": "言語変更はプログラムを再起動すると適用されます。",
        "기존 맵 데이터를 읽을 수 없습니다.\n{error}": "既存のマップデータを読み込めません。\n{error}",
        "이미지 위치: {x}, {y}": "画像位置: {x}, {y}",
        "이미지를 열 수 없습니다.\n{error}": "画像を開けません。\n{error}",
        "이미지 크기 변경": "画像サイズの変更",
        "교체 이미지의 크기가 기존 이미지와 다릅니다.\n\n예: 기준점 위치를 이미지 크기 비율에 맞춰 조정\n아니요: 기존 기준점을 모두 삭제\n취소: 이미지 교체 중단": "差し替え画像のサイズが既存の画像と異なります。\n\nはい: 基準点を画像サイズの比率に合わせて調整\nいいえ: 既存の基準点をすべて削除\nキャンセル: 画像の差し替えを中止",
        "기준점 {count}개 · {needed}개 더 필요": "基準点 {count}個・あと{needed}個必要",
        "기준점 {count}개 · 계산 가능": "基準点 {count}個・計算可能",
        "기준점 {count}개\n평균 오차 {rmse:.2f}px · 최대 {maximum:.2f}px": "基準点 {count}個\n平均誤差 {rmse:.2f}px・最大 {maximum:.2f}px",
        "계산 불가": "計算できません",
        "등록한 기준점을 모두 삭제할까요?": "登録した基準点をすべて削除しますか？",
        "맵 이미지를 먼저 불러오세요.": "先にマップ画像を開いてください。",
        "맵 좌표 데이터를 저장했습니다.\n{path}": "マップ座標データを保存しました。\n{path}",
        "저장된 맵": "保存済みマップ",
        "저장된 맵 데이터가 없습니다.": "保存済みのマップデータがありません。",
        "저장된 이미지 파일을 찾을 수 없습니다.\n{path}\n\n다른 이미지로 교체할까요?": "保存された画像ファイルが見つかりません。\n{path}\n\n別の画像に差し替えますか？",
        "삭제할 맵을 선택해 주세요.": "削除するマップを選択してください。",
        "이름 없음": "名前なし",
        "저장된 맵 삭제": "保存済みマップの削除",
        "'{name}'을 맵 데이터에서 삭제할까요?\n\n맵 이미지 파일은 삭제하지 않습니다.": "「{name}」をマップデータから削除しますか？\n\nマップ画像ファイルは削除されません。",
        "'{name}'을 맵 데이터에서 삭제했습니다.": "「{name}」をマップデータから削除しました。",
        "(빈 ID)": "(空のID)",
        "'{map_id}'는 사용할 수 없습니다.\n영문·숫자·밑줄·하이픈만 사용해 주세요.": "「{map_id}」は使用できません。\n英数字・アンダースコア・ハイフンのみ使用してください。",
        "'{map_id}' ID가 두 번 이상 사용됐습니다.": "ID「{map_id}」が複数回使用されています。",
        "'{name}': 한국어·일본어·영어 중 한 언어 이상의 맵 이름을 입력해 주세요.": "「{name}」: 韓国語・日本語・英語のうち、少なくとも1つの言語でマップ名を入力してください。",
        "{count}개 맵의 이름 패턴을 저장했습니다.": "{count}件のマップ名パターンを保存しました。",
        "'{name}' ({map_id}) 데이터가 이미 있습니다.\n가져온 자료로 교체할까요?\n\n예: 교체\n아니요: 기존 자료 유지\n취소: 전체 합치기 중단": "「{name}」({map_id}) のデータは既に存在します。\n読み込んだデータに置き換えますか？\n\nはい: 置換\nいいえ: 既存データを維持\nキャンセル: 統合を中止",
        "작업자료를 합칠 수 없습니다.\n{error}": "作業データを統合できません。\n{error}",
        "추가 {added}개 · 교체 {replaced}개 · 유지 {skipped}개\n맵별 파일은 다음 폴더에 저장됩니다.\n{path}": "追加 {added}件・置換 {replaced}件・維持 {skipped}件\nマップ別ファイルは次のフォルダーに保存されます。\n{path}",
    },
    "en": {
        "GodiNavi 좌표 매핑 도구": "GodiNavi Coordinate Calibrator",
        "맵 이미지 불러오기": "Open Map Image",
        "현재 이미지 교체": "Replace Current Image",
        "저장된 맵 불러오기": "Open Saved Map",
        "맵 이름 일괄 편집": "Batch Edit Names",
        "월드맵 위치 편집": "Edit World Map Positions",
        "월드맵 px": "World Map px",
        "1. 월드맵에서 위치 클릭\n2. 목록에서 맵 선택\n3. 선택 맵 연결 버튼": "1. Click a position on the world map\n2. Select a map from the list\n3. Link the selected map",
        "선택 맵 연결": "Link Selected Map",
        "연결 삭제": "Remove Link",
        "연결할 맵을 선택해 주세요.": "Select a map to link.",
        "월드맵에서 위치를 먼저 클릭해 주세요.": "Click a position on the world map first.",
        "연결을 삭제할 맵을 선택해 주세요.": "Select a map whose link should be removed.",
        "월드맵 이미지를 찾을 수 없습니다.\n{path}": "The world map image could not be found.\n{path}",
        "작업자료 합치기": "Merge Work Files",
        "현재 맵 저장": "Save Current Map",
        "맵 정보": "Map Information",
        "한국어": "Korean",
        "일본어": "Japanese",
        "영어": "English",
        "+ 패턴 추가": "+ Add Pattern",
        "기준점": "Control Points",
        "이미지에서 위치를 클릭한 뒤 게임 X:Y를 입력하세요.": "Click a position in the image, then enter its in-game X:Y.",
        "빈 곳 클릭: 기준점 추가 · 점 클릭: 선택\nCtrl+좌드래그: 점 이동 · Ctrl+휠: 확대/축소\n우클릭 드래그: 화면 이동 · 분산된 기준점 4개 이상 권장": "Click empty area: add point · Click point: select\nCtrl+left-drag: move point · Ctrl+wheel: zoom\nRight-drag: pan view · Use 4+ well-spaced points",
        "검증 오차": "Validation Error",
        "뚜렷한 이상 기준점 없음": "No clear outlier found",
        "확인 필요: 기준점 #{number} · 검증 오차 {error:.1f}px": "Check point #{number} · Validation error {error:.1f}px",
        "기준점 {count}개\n평균 오차 {rmse:.2f}px · 최대 {maximum:.2f}px\n{suspect}": "Control points: {count}\nAverage error {rmse:.2f}px · Max {maximum:.2f}px\n{suspect}",
        "최소 3점, 권장 4~6점입니다.": "At least 3 points are required; 4–6 are recommended.",
        "게임 X:Y": "Game X:Y",
        "이미지 px": "Image px",
        "선택점 삭제": "Delete Selected",
        "게임 좌표 편집": "Edit Game Coordinates",
        "편집할 기준점을 선택해 주세요.": "Select a control point to edit.",
        "전체 삭제": "Delete All",
        "계산 전": "Not calculated",
        "계산 가능": "Ready to calculate",
        "좌표 변환 계산": "Calculate Transform",
        "예상 위치 찾기": "Estimate Location",
        "위치 추측 불가": "Cannot Estimate Location",
        "위치 추측을 위해 기준점을 하나 이상 입력해 주세요.": "Enter at least one control point to estimate a location.",
        "찾을 게임 좌표를 X:Y 형식으로 입력해 주세요.": "Enter the game coordinates to find in X:Y format.",
        "위치 추측에 사용할 측량 완료 지도가 없습니다.": "There are no calibrated maps available for location estimation.",
        "같은 지역의 측량 자료": "calibrated maps from the same area",
        "전체 측량 자료": "all calibrated maps",
        "예상 위치 X:Y {x}:{y}\n{source} {count}개 기준 · 노란 영역은 추측 범위": "Estimated location X:Y {x}:{y}\nBased on {count} {source} · Yellow box is the estimated range",
        "맵 이미지를 불러오세요": "Open a map image",
        "게임 좌표 입력": "Enter Game Coordinates",
        "이미지 위치": "Image position",
        "게임 X": "Game X",
        "게임 Y": "Game Y",
        "입력 확인": "Check Input",
        "X와 Y는 정수로 입력해 주세요.": "Enter X and Y as integers.",
        "저장된 맵 선택": "Select Saved Map",
        "한국어 이름": "Korean Name",
        "일본어 이름": "Japanese Name",
        "영어 이름": "English Name",
        "기준점 수": "Control Points",
        "이미지": "Image",
        "선택 맵 삭제": "Delete Selected Map",
        "불러오기": "Open",
        "등록된 맵": "Registered Maps",
        "대표 이름": "Primary Name",
        "맵 ID": "Map ID",
        "언어별 이름 패턴": "Name Patterns by Language",
        "자동 예측": "Auto Predict",
        "자동 예측 완료": "Auto Prediction Complete",
        "자동 예측 불가": "Cannot Auto Predict",
        "자동 예측의 기준이 될 맵을 선택해 주세요.": "Select the map to use as the basis for auto prediction.",
        "선택한 맵의 이미지 파일명에서 층 번호를 찾을 수 없습니다.": "No floor number was found in the selected map's image filename.",
        "같은 파일명 형식의 다른 번호 이미지를 찾지 못했습니다.": "No other numbered images with the same filename pattern were found.",
        "예측할 연속 이미지가 없거나 입력한 이름에서 현재 층 번호를 찾지 못했습니다.": "No image series was available, or the current floor number was not found in the entered name.",
        "연속된 이미지의 맵 이름 {count}개를 자동으로 채웠습니다.\n내용을 확인한 뒤 전체 이름 저장을 눌러 주세요.": "Automatically filled names for {count} maps in the image series.\nReview them, then click Save All Names.",
        "한 줄에 패턴 하나를 입력합니다. 첫 번째 줄이 대표 이름입니다.": "Enter one pattern per line. The first line is the primary name.",
        "영문·숫자·밑줄(_)·하이픈(-)만 사용": "Use letters, numbers, underscores (_) and hyphens (-) only",
        "취소": "Cancel",
        "전체 이름 저장": "Save All Names",
        "저장 완료": "Saved",
        "삭제 완료": "Deleted",
        "저장 불가": "Cannot Save",
        "한국어·일본어·영어 중 한 언어 이상의 맵 이름을 입력해 주세요.": "Enter a map name in at least one language: Korean, Japanese, or English.",
        "선택 필요": "Selection Required",
        "이미지 없음": "Image Missing",
        "이미지 오류": "Image Error",
        "데이터 오류": "Data Error",
        "합치기 완료": "Merge Complete",
        "합치기 실패": "Merge Failed",
        "동일한 맵 ID 발견": "Duplicate Map ID Found",
        "맵 ID 확인": "Check Map ID",
        "맵 ID 중복": "Duplicate Map ID",
        "추가": "Added",
        "교체": "Replaced",
        "유지": "Kept",
        "기존 자료 유지": "Keep existing data",
        "전체 합치기 중단": "Cancel entire merge",
        "맵별 파일은 다음 폴더에 저장됩니다.": "Per-map files are stored in the following folder.",
        "맵 이미지 선택": "Select Map Image",
        "연속 이미지 일괄 등록": "Register Image Series",
        "같은 폴더에서 번호가 이어지는 이미지 {count}개를 찾았습니다.\n\n다른 이미지도 함께 사전 저장하시겠습니까?\n맵 이름과 파일명의 번호를 대응하여 자동으로 개별 맵 데이터를 생성합니다.\n나머지 이미지의 기준점은 비어 있는 상태로 저장됩니다.": "Found {count} numbered images in the same folder.\n\nPre-register the other images too?\nSeparate map data will be generated automatically by matching the numbers in the map names and filenames.\nControl points for the remaining images will be saved empty.",
        "{count}개 맵 데이터를 각각 저장했습니다.\n나머지 이미지의 기준점은 비어 있습니다.": "Saved {count} map records separately.\nControl points for the remaining images are empty.",
        "교체할 맵 이미지 선택": "Select Replacement Image",
        "대체할 맵 이미지 선택": "Select Replacement Map Image",
        "합칠 맵 작업자료 선택": "Select Map Work Files to Merge",
        "맵 JSON": "Map JSON",
        "모든 파일": "All Files",
        "평균 오차": "Average error",
        "최대": "Max",
        "개 더 필요": " more required",
        "개": "",
        "기준점이 최소 4개 필요합니다.": "At least 4 control points are required.",
        "기준점이 한 직선에 몰려 있습니다. 서로 다른 방향으로 퍼진 점을 지정해 주세요.": "The control points are collinear. Place points spread in different directions.",
        "언어 설정": "Language",
        "언어 변경은 프로그램을 다시 실행하면 적용됩니다.": "Restart the program to apply the language change.",
        "기존 맵 데이터를 읽을 수 없습니다.\n{error}": "Could not read the existing map data.\n{error}",
        "이미지 위치: {x}, {y}": "Image position: {x}, {y}",
        "이미지를 열 수 없습니다.\n{error}": "Could not open the image.\n{error}",
        "이미지 크기 변경": "Image Size Changed",
        "교체 이미지의 크기가 기존 이미지와 다릅니다.\n\n예: 기준점 위치를 이미지 크기 비율에 맞춰 조정\n아니요: 기존 기준점을 모두 삭제\n취소: 이미지 교체 중단": "The replacement image size differs from the existing image.\n\nYes: Scale control points to the new image size\nNo: Delete all existing control points\nCancel: Do not replace the image",
        "기준점 {count}개 · {needed}개 더 필요": "Control points: {count} · {needed} more required",
        "기준점 {count}개 · 계산 가능": "Control points: {count} · Ready to calculate",
        "기준점 {count}개\n평균 오차 {rmse:.2f}px · 최대 {maximum:.2f}px": "Control points: {count}\nAverage error {rmse:.2f}px · Max {maximum:.2f}px",
        "계산 불가": "Cannot Calculate",
        "등록한 기준점을 모두 삭제할까요?": "Delete all registered control points?",
        "맵 이미지를 먼저 불러오세요.": "Open a map image first.",
        "맵 좌표 데이터를 저장했습니다.\n{path}": "Map coordinate data saved.\n{path}",
        "저장된 맵": "Saved Maps",
        "저장된 맵 데이터가 없습니다.": "There is no saved map data.",
        "저장된 이미지 파일을 찾을 수 없습니다.\n{path}\n\n다른 이미지로 교체할까요?": "The saved image file could not be found.\n{path}\n\nReplace it with another image?",
        "삭제할 맵을 선택해 주세요.": "Select a map to delete.",
        "이름 없음": "Unnamed",
        "저장된 맵 삭제": "Delete Saved Map",
        "'{name}'을 맵 데이터에서 삭제할까요?\n\n맵 이미지 파일은 삭제하지 않습니다.": "Delete '{name}' from the map data?\n\nThe map image file will not be deleted.",
        "'{name}'을 맵 데이터에서 삭제했습니다.": "'{name}' was deleted from the map data.",
        "(빈 ID)": "(empty ID)",
        "'{map_id}'는 사용할 수 없습니다.\n영문·숫자·밑줄·하이픈만 사용해 주세요.": "'{map_id}' cannot be used.\nUse only letters, numbers, underscores, and hyphens.",
        "'{map_id}' ID가 두 번 이상 사용됐습니다.": "The ID '{map_id}' is used more than once.",
        "'{name}': 한국어·일본어·영어 중 한 언어 이상의 맵 이름을 입력해 주세요.": "'{name}': Enter a map name in at least one language: Korean, Japanese, or English.",
        "{count}개 맵의 이름 패턴을 저장했습니다.": "Saved name patterns for {count} maps.",
        "'{name}' ({map_id}) 데이터가 이미 있습니다.\n가져온 자료로 교체할까요?\n\n예: 교체\n아니요: 기존 자료 유지\n취소: 전체 합치기 중단": "Data for '{name}' ({map_id}) already exists.\nReplace it with the imported data?\n\nYes: Replace\nNo: Keep existing data\nCancel: Stop the entire merge",
        "작업자료를 합칠 수 없습니다.\n{error}": "Could not merge the work data.\n{error}",
        "추가 {added}개 · 교체 {replaced}개 · 유지 {skipped}개\n맵별 파일은 다음 폴더에 저장됩니다.\n{path}": "Added {added} · Replaced {replaced} · Kept {skipped}\nPer-map files are stored in the following folder.\n{path}",
    },
}


def detect_windows_language():
    try:
        buffer = ctypes.create_unicode_buffer(85)
        ctypes.windll.kernel32.GetUserDefaultLocaleName(buffer, len(buffer))
        tag = buffer.value.lower()
    except Exception:
        tag = ""
    if tag.startswith("ja"):
        return "ja"
    if tag.startswith("ko"):
        return "ko"
    return "en"


def load_language(settings_path):
    try:
        payload = json.loads(Path(settings_path).read_text(encoding="utf-8"))
        shared_value = payload.get("ui_language")
        value = {"KR": "ko", "JP": "ja", "EN": "en"}.get(str(shared_value).upper())
        if value is None:
            value = payload.get("uiLanguage")
        if value in LANGUAGE_LABELS:
            return value
    except Exception:
        pass
    return detect_windows_language()


def save_language(settings_path, language):
    path = Path(settings_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            payload = {}
    except Exception:
        payload = {}
    payload["ui_language"] = {"ko": "KR", "ja": "JP", "en": "EN"}.get(language, "EN")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def set_language(language):
    global CURRENT_LANGUAGE
    CURRENT_LANGUAGE = language if language in LANGUAGE_LABELS else "en"


def tr(text):
    if CURRENT_LANGUAGE == "ko" or not isinstance(text, str):
        return text
    translations = TRANSLATIONS[CURRENT_LANGUAGE]
    if text in translations:
        return translations[text]
    result = text
    for source in sorted(translations, key=len, reverse=True):
        result = result.replace(source, translations[source])
    return result


def localize_widget_tree(widget):
    # Keep the original Korean source text so the same live widget can be
    # translated repeatedly (KR -> JP -> EN -> KR) without restarting.
    try:
        source_text = getattr(widget, "_locale_source_text", None)
        if source_text is None:
            source_text = widget.cget("text")
            widget._locale_source_text = source_text
        if source_text:
            widget.configure(text=tr(source_text))
    except Exception:
        pass

    # Tk and Toplevel captions are not exposed through cget("text").
    try:
        source_title = getattr(widget, "_locale_source_title", None)
        if source_title is None:
            source_title = widget.title()
            widget._locale_source_title = source_title
        if source_title:
            widget.title(tr(source_title))
    except Exception:
        pass

    for child in widget.winfo_children():
        localize_widget_tree(child)
