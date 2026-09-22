"""预置校园知识库（虚构"示例大学"信息），供校园Agent RAG 问答演示。

用法：.venv\\Scripts\\python.exe scripts\\seed_demo.py
重复运行会跳过已存在的内置文档。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
os.chdir(os.path.join(os.path.dirname(__file__), "..", "backend"))
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")  # 国内镜像
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")  # 镜像不支持 Xet

from app.database import get_conn, init_db  # noqa: E402
from app.services import doc_service  # noqa: E402

DOCS = [
    ("图书馆开放与服务指南", """示例大学图书馆开放时间为周一至周五 8:00-22:00，周六周日 9:00-21:00，法定节假日闭馆。
入馆需刷校园卡。主馆位于校园中心，共6层：一层为借还书服务台与自助打印区；二层至四层为社科与自然科学借阅区；五层为自习区（需预约，可在"示例大学图书馆"微信公众号提前1天预约）；六层为研讨间，支持4-8人小组讨论预约。
图书借阅规则：本科生可借15册，借期30天，可续借1次；研究生可借25册，借期45天。超期罚款0.1元/天/册。考试周期间（以教务处通知为准）五层自习区开放至24:00。
图书馆每月最后一周周五下午闭馆整理。""", "campus"),
    ("教务系统与选课指南", """示例大学教务系统入口为 jw.sample.edu.cn，使用学号与统一身份认证密码登录。
选课分三轮：第一轮预选（每学期第14周）、第二轮抢选（开学前一周）、第三轮补退选（开学第1-2周）。每学期本科生限选35学分，挂科需重修。
成绩查询在教务系统"成绩服务"栏目，期末成绩于考试结束后10个工作日内发布。对成绩有异议可在发布后5个工作日内向开课学院提交复核申请。
转专业申请每年一次，大一下学期第8周在教务系统提交，要求无挂科记录且绩点排名专业前40%。""", "campus"),
    ("奖学金与评优办事流程", """国家奖学金评定每年9月启动：学生本人向学院提交申请表、成绩单与获奖证明，学院初审公示5个工作日后报学生处复审，10月底公布结果。
学业奖学金覆盖前30%（一等5000元、二等3000元）。申请流程：登录学生工作管理系统（xg.sample.edu.cn）在线填写→导出PDF签字→交辅导员。
评优材料造假将取消资格并记入诚信档案。咨询渠道：学生处综合科，行政楼302，电话 010-6688-0000。""", "campus"),
    ("社团活动与校园活动一览", """示例大学共有注册社团86个，覆盖学术科技、文化艺术、体育健身、志愿公益四大类。
百团大战（社团招新）于每年9月第三周在文化广场举行。知名社团：机器人协会（曾获全国机器人大赛一等奖）、辩论队、天文学社、街舞社。
创新创业类活动：每年3月"互联网+"校赛启动，5月挑战杯校赛，10月iCAN创新创业大赛校内选拔；参赛团队可申请大创项目经费（国家级2万元/项）。
学术讲座信息发布于官网"讲座预告"栏目及各学院公众号，多数讲座需通过第二课堂小程序报名签到。""", "campus"),
    ("校园卡、宿舍与后勤服务", """校园卡办理：新生报到时在后勤服务大厅（生活区1号楼）凭录取通知书领取。充值可通过"示例大学"App或支付宝校园生活号。校园卡可在食堂、超市、图书馆、澡堂使用。
宿舍门禁时间：23:00-6:00（周日至周四），周五周六 24:00-6:00。宿舍报修通过"掌上后勤"小程序，一般48小时内响应。
医务室位于校医院楼一楼，工作日 8:00-17:00，急诊24小时。医保报销每年12月集中受理。
失物招领：保卫处值班室（校门口东侧），也可在"示例大学失物招领"平台登记。""", "campus"),
]

if __name__ == "__main__":
    init_db()
    with get_conn() as conn:
        existing = {r["filename"] for r in conn.execute(
            "SELECT filename FROM documents WHERE builtin = 1").fetchall()}
    added = 0
    for title, text, scene in DOCS:
        if title in existing:
            print(f"跳过（已存在）: {title}")
            continue
        r = doc_service.ingest_text(title, text, scene=scene, builtin=True)
        added += 1
        print(f"已入库: {title} -> chunks={r['chunk_count']}")
    print(f"完成，新增 {added} 篇。")
