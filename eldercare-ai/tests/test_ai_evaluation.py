"""Quality gates for the local classifiers. Thresholds sit below measured values to catch regressions."""
from src.ai.evaluate import run


def test_classifier_quality_gates():
    res = run()
    h = res["_hybrid"]
    assert res["Intent classifier, standard set"]["accuracy"] >= 0.90
    assert res["Intent classifier, hard set (typos, indirect phrasing)"]["accuracy"] >= 0.80
    assert res["Urgency classifier, FRESH set (not used for tuning)"]["accuracy"] >= 0.70
    for name in ("development set", "fresh set"):
        assert h[name]["hybrid_recall"] == 1.0          # no missed emergencies in either test set
        assert h[name]["false_alarms"] == []            # and no false alarms on non-emergencies


def test_other_ai_components_quality_gates():
    res = run()
    assert res["_rag"]["hit1"] >= 0.75 and res["_rag"]["hit3"] >= 0.85
    assert res["_reminder"]["accuracy"] >= 0.9
    assert res["_doc"]["recall"] >= 0.75 and res["_doc"]["precision"] >= 0.75
    sn = res["_sensor"]
    assert sn["fall"]["fall"] >= 0.95 and sn["fall_soft"]["fall"] >= 0.95            # synthetic data only
    for sc in ("standing", "sitting", "walking", "sit_hard"):
        assert sn[sc]["none"] >= 0.95
    assert sn["stairs"]["none"] >= 0.8 and sn["stumble"]["fall"] == 0.0               # a stumble is not called a fall


def test_evaluation_is_repeatable():
    a, b = run(), run()
    assert a["Intent classifier, standard set"]["accuracy"] == b["Intent classifier, standard set"]["accuracy"]
    assert a["_hybrid"] == b["_hybrid"]
