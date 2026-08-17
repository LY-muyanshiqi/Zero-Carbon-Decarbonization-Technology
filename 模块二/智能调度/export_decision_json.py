# -*- coding: utf-8 -*-
"""
导出调度建议为 JSON，供静态 HTML 调度建议页读取渲染。

用法：python export_decision_json.py [目标日下标] [输出json路径]
默认：目标日最后一天，输出到 智能调度/output/调度建议.json
"""

import sys
import os
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
from decision_engine import run_daily_decision


def export(target_day_idx=-1, out_path=None):
    result = run_daily_decision(target_day_idx=target_day_idx, k=5, use_load_forecast=False)
    if "error" in result:
        print("导出失败:", result["error"])
        return

    res = result["res"]
    hourly = result["hourly"]
    summary = result["summary"]

    # 组装前端需要的结构
    payload = {
        "summary": summary,
        "hourly": hourly,
        # 便于 ECharts 直接用的数值数组
        "series": {
            "hours": [h["小时"] for h in hourly],
            "load": [h["预测负荷_kW"] for h in hourly],
            "pv": [h["预测光伏_kW"] for h in hourly],
            "grid_buy": [h["购电_kW"] for h in hourly],
            "flex_down": [h["曝气下调_kW"] for h in hourly],
            "soc": [h["SOC"] for h in hourly],
            "battery_action": [h["储能动作"] for h in hourly],
            "pv_action": [h["光伏去向"] for h in hourly],
        },
    }

    if out_path is None:
        # 默认导出到脚本同目录，与 调度建议.html 同目录，便于浏览器 fetch
        out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "调度建议.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"已导出调度建议 JSON: {out_path}")
    return out_path


if __name__ == "__main__":
    target_idx = int(sys.argv[1]) if len(sys.argv) > 1 else -1
    out = sys.argv[2] if len(sys.argv) > 2 else None
    export(target_idx, out)
