import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bpc.branch_and_price import BranchAndPrice
from test.pcp_reader import read_pcp_instance
from ev.ev_to_pcp import load_ev_instance

# ============ 定义 QAIA 使用开关 ============
USE_QAIA = True # 设置为 True 使用 QAIA ，设置为 False 不使用

def test_branch_and_price_from_pcp():
    """测试分支定价算法"""
    
    # 读取测试实例并构造 Instance（包含 graph 和 charger_num）。
    # 注意：这里的 charger_num 需要由调用者显式给出，
    # 真实 EV 算例应优先通过 ev.ev_to_pcp.load_ev_instance 从 JSON 中读取。
    charger_num = 20  # TODO: 根据具体算例含义调整或从外部配置读取
    instance = read_pcp_instance("data/ev_instances/ev_V10_C2_T12_dur1_vpc5.json", charger_num=charger_num)
    graph = instance.graph
    charger_num = instance.charger_num

    print(
        f"成功读取图: {len(graph.vertices)}顶点, "
        f"{len(graph.edges)}边, "
        f"{len(graph.partitions)}分区, "
        f"充电桩数量: {charger_num}"
    )

    # 创建分支定价算法对象
    bp = BranchAndPrice(graph, charger_num, time_limit=3600, use_qaia=USE_QAIA)
    result = bp.solve()
    return result


def test_branch_and_price_from_ev():
    ev_path = "data/ev_instances/ev_V10_C2_T12_dur1_vpc5.json"

    instance = load_ev_instance(ev_path)
    graph = instance.graph
    charger_num = instance.charger_num

    print(f"测试算例: {instance}")
    print(f"是否启用QAIA: {USE_QAIA}")
    print(f"车辆数量: {len(graph.partitions)}")
    print(f"充电桩数量: {charger_num}")

    bp = BranchAndPrice(
        graph,
        charger_num,
        time_limit=3600,
        use_qaia=USE_QAIA
    )
    return bp.solve()

if __name__ == "__main__":
    # 默认运行 EV 算例测试；如需运行传统 PCP 测试，可调用 test_branch_and_price()
    test_branch_and_price_from_ev()



