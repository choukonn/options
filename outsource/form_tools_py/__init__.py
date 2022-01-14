#!/usr/bin/python3

import form_tools_py.conf
import form_tools_py.common
import form_tools_py.read_i18n_translation
import form_tools_py.getXmlSid

# コンフィグ
config_data = {}

# XMLなm_outsourceを丸ごと
outsource_config = {}

# 言語対応関係
i18n_list = []
i18n_item = {}

# DBの情報
m_section = {}
m_qualitative = {}
m_opinion_rankset = {}

# 受診者情報
examinee = {}
