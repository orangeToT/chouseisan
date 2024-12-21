import pandas as pd
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpStatus, value

def create_shift_schedule(csv_path, output_csv_path):
    # CSVファイルを読み込む
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()
    
    # タイトル行を取得
    title_line = lines[0].strip()
    
    # データ部分を読み込む（最初の行と最後のコメント行をスキップ）
    df = pd.read_csv(csv_path, skiprows=1, skipfooter=1, engine='python')
    dates = df['日程'].tolist()
    people = df.columns[1:].tolist()

    # 利用可能性のマッピング
    availability = {p: [] for p in people}
    for person in people:
        availability[person] = df[df[person] == '◯']['日程'].tolist()

    # 線形計画問題の定義
    prob = LpProblem("Shift_Scheduling", LpMinimize)

    # 変数の定義
    assign = LpVariable.dicts("assign", [(d, p) for d in dates for p in people], cat='Binary')

    # 各日付に一人だけ割り当てる制約
    for d in dates:
        prob += lpSum([assign[(d, p)] for p in people]) == 1, f"One_person_per_day_{d}"

    # 各人の割り当て可能な日付のみ割り当てる制約
    for p in people:
        for d in dates:
            if d not in availability[p]:
                prob += assign[(d, p)] == 0, f"Availability_{d}_{p}"

    # 各人の合計割り当て数
    total_assignments = {p: lpSum([assign[(d, p)] for d in dates]) for p in people}

    # 平均割り当て数
    avg_assign = sum(total_assignments[p] for p in people) / len(people)

    # 分散を最小化するために各人の割り当て数と平均の差の絶対値を変数として定義
    deviations = LpVariable.dicts("deviation", people, lowBound=0, cat='Continuous')

    for idx, p in enumerate(people):
        # 制約名にインデックスを追加して一意にする
        prob += total_assignments[p] - avg_assign <= deviations[p], f"Deviation_positive_{idx}_{p}"
        prob += avg_assign - total_assignments[p] <= deviations[p], f"Deviation_negative_{idx}_{p}"

    # 目的関数: 分散の代わりに偏差の合計を最小化
    prob += lpSum([deviations[p] for p in people]), "Minimize_deviation"

    # 問題を解く
    prob.solve()

    # 結果の保存
    if LpStatus[prob.status] == 'Optimal':
        schedule = {}
        for d in dates:
            for p in people:
                if value(assign[(d, p)]) == 1:
                    schedule[d] = p
                    break
        
        # 新しいデータフレームを作成
        assign_df = pd.DataFrame(columns=df.columns)
        assign_df['日程'] = dates
        for p in people:
            assign_df[p] = '×'
        
        for d, p in schedule.items():
            assign_df.loc[assign_df['日程'] == d, p] = '◯'
        
        # 出力CSVファイルにタイトル行と割り当て結果を書き込む
        with open(output_csv_path, 'w', encoding='utf-8-sig') as f_out:
            f_out.write(title_line + '\n')
            assign_df.to_csv(f_out, index=False)
        
        print(f"スケジュールが '{output_csv_path}' に保存されました。")
    else:
        print("最適解が見つかりませんでした。")

# 使用例
if __name__ == "__main__":
    create_shift_schedule('chouseisan.csv', 'chouseisan_output_csv.csv') 