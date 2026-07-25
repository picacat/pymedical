
# -*- coding: UTF-8 -*-


from PyQt5 import QtWidgets, QtCore
from libs import nhi_utils
from libs import statistics_utils
from libs import system_utils


# 系統設定 2018.03.19
class LoginStatistics(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(LoginStatistics, self).__init__(parent)
        self.database = args[0]
        self.system_settings = args[1]
        self.user_name = args[2]
        self.parent = parent

        if self.system_settings.field('候診名單病歷統計顯示全院統計') == 'Y':
            self.user_name = '全部'

        self.statistics_dicts = {
            '本月健保內科人數': 0,
            '本月健保針灸人數': 0,
            '本月健保中度複針人數': 0,
            '本月健保高度複針人數': 0,
            '本月健保針傷合併人數': 0,
            '本月健保傷科人數': 0,
            '本月健保中度複傷人數': 0,
            '本月健保高度複傷人數': 0,
            '本月健保脫臼整復人數': 0,
            '本月健保針傷給藥人數': 0,
            '本月健保首次人數': 0,
            '本月健保看診日數': 0,
            '第一段診察費合理量': 0,
            '本月健保診察費人數': 0,
            '本月健保針傷限量': 0,
            '本月健保針傷合計': 0,
            '本日健保內科人數': 0,
            '本日健保針灸人數': 0,
            '本日健保傷科人數': 0,
            '本日健保首次人數': 0,
        }

        self._set_ui()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def _set_ui(self):
        system_utils.center_window(self)

    def start_statistics(self):
        self._calc_general_count()

        self.close()

    def _calc_general_count(self):
        max_progress = 16
        progress_dialog = QtWidgets.QProgressDialog(
            '正在統計資料中, 請稍後...', '取消', 0, max_progress, self
        )

        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        self.statistics_dicts['本月健保內科人數'] = statistics_utils.get_count_by_treat_type(
            self.database, 'cases', '當月', ['內科', '一般'], self.user_name,
        )
        progress_dialog.setValue(1)
        self.statistics_dicts['本月健保針灸人數'] = statistics_utils.get_count_by_treat_type(
            self.database, 'cases', '當月', nhi_utils.ACUPUNCTURE_TREAT, self.user_name,
        )
        progress_dialog.setValue(2)
        self.statistics_dicts['本月健保傷科人數'] = statistics_utils.get_count_by_treat_type(
            self.database, 'cases', '當月', nhi_utils.MASSAGE_TREAT + nhi_utils.DISLOCATE_TREAT, self.user_name
        )
        progress_dialog.setValue(3)
        self.statistics_dicts['本月健保首次人數'] = statistics_utils.get_first_course(
            self.database, 'cases', '當月',
        )
        progress_dialog.setValue(4)
        self.statistics_dicts['本月健保看診日數'] = statistics_utils.get_diag_days(self.database, self.user_name)

        progress_dialog.setValue(5)
        self.statistics_dicts['本月健保診察費人數'] = statistics_utils.get_diag_case(self.database, self.user_name)

        progress_dialog.setValue(6)
        self.statistics_dicts['第一段診察費合理量'] = self.statistics_dicts['本月健保看診日數'] * nhi_utils.DIAG_SECTION1

        progress_dialog.setValue(7)
        self.statistics_dicts['本月健保針傷限量'] = statistics_utils.get_max_treat(self.database, self.user_name)

        progress_dialog.setValue(8)
        self.statistics_dicts['本月健保中度複針人數'] = statistics_utils.get_count_by_treat_type(
            self.database, 'cases', '當月',
            nhi_utils.MODERATE_COMPLICATED_ACUPUNCTURE_LIST, self.user_name,
        )

        progress_dialog.setValue(9)
        self.statistics_dicts['本月健保高度複針人數'] = statistics_utils.get_count_by_treat_type(
            self.database, 'cases', '當月',
            nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_LIST, self.user_name,
        )

        progress_dialog.setValue(10)
        self.statistics_dicts['本月健保中度複針限量'] = nhi_utils.MAX_MODERATE_COMPLICATED_ACUPUNCTURE

        progress_dialog.setValue(11)
        self.statistics_dicts['本月健保高度複針限量'] = nhi_utils.MAX_HIGHLY_COMPLICATED_ACUPUNCTURE

        self.statistics_dicts['本月健保針傷合併限量'] = nhi_utils.MAX_MERGE_TREAT

        progress_dialog.setValue(12)
        self.statistics_dicts['本月健保針傷合併人數'] = statistics_utils.get_count_by_treat_type(
            self.database, 'cases', '當月', nhi_utils.MERGE_TREAT_LIST, self.user_name, merge_treat=True
        )

        progress_dialog.setValue(13)
        self.statistics_dicts['本月健保中度複傷人數'] = statistics_utils.get_count_by_treat_type(
            self.database, 'cases', '當月',
            nhi_utils.MODERATE_COMPLICATED_MASSAGE_TREAT + nhi_utils.MODERATE_COMPLICATED_MASSAGE_TREAT,
            self.user_name,
        )

        progress_dialog.setValue(14)
        self.statistics_dicts['本月健保高度複傷人數'] = statistics_utils.get_count_by_treat_type(
            self.database, 'cases', '當月',
            nhi_utils.HIGHLY_COMPLICATED_MASSAGE_TREAT, self.user_name,
        )

        progress_dialog.setValue(15)
        self.statistics_dicts['本月健保脫臼整復人數'] = statistics_utils.get_count_by_treat_type(
            self.database, 'cases', '當月', ['脫臼整復復位', '脫臼整復復位'], self.user_name,
        )

        # progress_dialog.setValue(16)
        # self.statistics_dicts['本月健保骨折復位人數'] = statistics_utils.get_count_by_treat_type(
        #     self.database, 'cases', '當月', ['骨折復位', '骨折復位'], self.user_name,
        # )

        if self.system_settings.field('統計針傷給藥人數') == 'Y':
            progress_dialog.setValue(16)
            self.statistics_dicts['本月健保針傷給藥人數'] = statistics_utils.get_treat_drug_count(
                self.database, '當月', self.user_name,
            )

        progress_dialog.setValue(max_progress)
        progress_dialog.deleteLater()
