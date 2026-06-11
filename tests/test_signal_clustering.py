from signal_clustering import DefaultSignalClusterer


def signal(signal_id: str, title: str, body: str) -> dict:
    return {
        "id": signal_id,
        "title": title,
        "body": body,
        "source": {
            "id": "fixture",
            "name": "Fixture",
            "published_at": "2026-06-09T08:00:00Z",
            "url": f"https://example.com/{signal_id}",
        },
    }


SERVE_THE_HOME_SIGNALS = [
    signal(
        "sth-1",
        "Minisforum S5 All-Flash NAS Shown Based on Intel's Wildcat Lake Platform",
        """<p>At Computex 2026 Minisforum was showing off their upcoming S5 NAS, a mid-range all-flash NAS. With 5 M.2 SSD slots and 10GbE networking, the fanless NAS punches up</p>
<p>The post <a href="https://www.servethehome.com/minisforum-s5-all-flash-nas-shown-based-on-intels-wildcat-lake-platform/">Minisforum S5 All-Flash NAS Shown Based on Intel&#8217;s Wildcat Lake Platform</a> appeared first on <a href="https://www.servethehome.com">ServeTheHome</a>.</p>""",
    ),
    signal(
        "sth-2",
        "ServeTheHome Turns 17 The Places You Will Go",
        """<p>ServeTheHome is now 17 years old, starting from posting about using RAID controllers and 2.5" hard drives and taking us all over</p>
<p>The post <a href="https://www.servethehome.com/servethehome-turns-17-the-places-you-will-go/">ServeTheHome Turns 17 The Places You Will Go</a> appeared first on <a href="https://www.servethehome.com">ServeTheHome</a>.</p>""",
    ),
    signal(
        "sth-3",
        "NXP Computex Keynote 2026 Coverage",
        """<p>The final keynote for Computex 2026 comes from NXP, where CEO Rafael Sotomayor is talking all about what it takes to deliver AI for edge devices and robotics in the real world, and how NXP is well-positioned to accomplish this</p>
<p>The post <a href="https://www.servethehome.com/nxp-computex-keynote-2026-coverage/">NXP Computex Keynote 2026 Coverage</a> appeared first on <a href="https://www.servethehome.com">ServeTheHome</a>.</p>""",
    ),
    signal(
        "sth-4",
        "A 40-Node 1U Cluster Gigabyte R1C7-K0A-AS1",
        """<p>At Computex 2026, we found the Gigabyte R1C7-K0A-AS1 which can put 40 nodes with 320 cores, 40 iGPUs and 80 SSDs in just 1U</p>
<p>The post <a href="https://www.servethehome.com/a-40-node-1u-cluster-gigabyte-r1c7-k0a-as1/">A 40-Node 1U Cluster Gigabyte R1C7-K0A-AS1</a> appeared first on <a href="https://www.servethehome.com">ServeTheHome</a>.</p>""",
    ),
    signal(
        "sth-5",
        "Scoping Out RTX Spark SFF Mini-PCs at Computex 2026",
        """<p>While at Computex, we caught a look at some of the upcoming SFF mini-PCs based on NVIDIA's RTX Spark SoC, including systems from ASUS, Dell, Lenovo, and MSI</p>
<p>The post <a href="https://www.servethehome.com/scoping-out-rtx-spark-sff-mini-pcs-at-computex-2026/">Scoping Out RTX Spark SFF Mini-PCs at Computex 2026</a> appeared first on <a href="https://www.servethehome.com">ServeTheHome</a>.</p>""",
    ),
    signal(
        "sth-6",
        "Microsoft to Join the AI Dev Mini-PC Market With Upcoming Surface RTX Spark Dev Box",
        """<p>Microsoft is joining the AI dev box mini-PC market with the announcement of the Surface RTX Spark Dev Box. Due later this year, it will offer a pre-loaded dev environment, powered by NVIDIA's new RTX Spark SoC</p>
<p>The post <a href="https://www.servethehome.com/microsoft-to-join-the-ai-dev-mini-pc-market-with-upcoming-surface-rtx-spark-dev-box/">Microsoft to Join the AI Dev Mini-PC Market With Upcoming Surface RTX Spark Dev Box</a> appeared first on <a href="https://www.servethehome.com">ServeTheHome</a>.</p>""",
    ),
]

CHINESE_SIGNALS = [
    signal("cn-1", "光模块订单", "北美云厂商上调800G光模块采购计划，2026年二季度订单环比增加35%，交付周期延长到10周。"),
    signal("cn-2", "电源交期1", "台系ODM反馈高功率电源模块交期从6周拉长到14周，主要受AI整机机柜功耗提升影响。"),
    signal("cn-3", "HBM产能1", "HBM3E供应商表示2026年产能已被大客户预订超过80%，先进封装排产因此延后到四季度。"),
    signal("cn-4", "液冷项目", "欧洲数据中心液冷改造项目在2026年下半年启动，单柜功率目标提升到120千瓦。"),
    signal("cn-5", "PCB材料", "高速PCB材料厂6月上调BT载板报价12%，交换机与服务器主板需求拉动排产。"),
    signal("cn-6", "服务器产线", "墨西哥服务器整机新产线开始试产，预计2026年底月产能提升至3万台。"),
    signal("cn-7", "HBM产能2", "HBM3E主要供应商称2026年产能预订已超过八成，大客户追加订单让先进封装排期推迟。"),
    signal("cn-8", "电源交期2", "AI服务器高功率电源模块供应继续吃紧，台系ODM称交付周期由6周延长至14周。"),
]


def cluster_ids(clusters):
    return [sorted(signal["id"] for signal in cluster.signals) for cluster in clusters]


def test_default_clusterer_groups_related_serve_the_home_rtx_signals_only():
    clusters = DefaultSignalClusterer().cluster(SERVE_THE_HOME_SIGNALS)

    assert cluster_ids(clusters) == [
        ["sth-1"],
        ["sth-2"],
        ["sth-3"],
        ["sth-4"],
        ["sth-5", "sth-6"],
    ]


def test_default_clusterer_groups_chinese_related_pairs_and_splits_distinct_events():
    clusters = DefaultSignalClusterer().cluster(CHINESE_SIGNALS)

    assert cluster_ids(clusters) == [
        ["cn-1"],
        ["cn-2", "cn-8"],
        ["cn-3", "cn-7"],
        ["cn-4"],
        ["cn-5"],
        ["cn-6"],
    ]


def test_default_clusterer_single_signal_is_singleton():
    clusters = DefaultSignalClusterer().cluster([SERVE_THE_HOME_SIGNALS[4]])

    assert cluster_ids(clusters) == [["sth-5"]]
    assert clusters[0].reason == "singleton"


def test_default_clusterer_small_batch_degrades_to_singletons():
    clusters = DefaultSignalClusterer().cluster(SERVE_THE_HOME_SIGNALS[4:6])

    assert cluster_ids(clusters) == [["sth-5"], ["sth-6"]]


def test_default_clusterer_df_filter_adapts_to_different_batch_common_terms():
    batch = [
        signal("a", "MegaConf 2030 Alpha Storage", "MegaConf 2030 Alpha shows NVMe Lake modules."),
        signal("b", "MegaConf 2030 Beta Robotics", "MegaConf 2030 Beta covers Robot Arm modules."),
        signal("c", "MegaConf 2030 Gamma Cloud", "MegaConf 2030 Gamma covers Cloud Rack modules."),
        signal("d", "MegaConf 2030 Delta Fabric", "MegaConf 2030 Delta covers Fabric Switch modules."),
        signal("e", "MegaConf 2030 Nova RTX Spark", "MegaConf 2030 Nova uses NVIDIA RTX Spark SoC modules."),
        signal("f", "MegaConf 2030 Orion RTX Spark", "MegaConf 2030 Orion uses NVIDIA RTX Spark SoC modules."),
    ]

    clusters = DefaultSignalClusterer().cluster(batch)

    assert cluster_ids(clusters) == [["a"], ["b"], ["c"], ["d"], ["e", "f"]]
