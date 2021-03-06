import pandas as pd
import numpy as np


# 该字典key为前端准备显示的所有多选字段名, value为数据库对应的字段名
D_list = {
    'TC I': 'TCI',
    'TC II': 'TCII',
    'TC III': 'TCIII',
    'TC IV': 'TCIV',
    '通用名|MOLECULE': 'MOLECULE',
    '商品名|PRODUCT': 'PRODUCT',
    '包装|PACKAGE': 'PACKAGE',
    '生产企业|CORPORATION': 'CORPORATION',
    '企业类型': 'MANUF_TYPE',
    '剂型': 'FORMULATION',
    '剂量': 'STRENGTH'
}

D_TRANS = {
            'MAT': '滚动年',
            'QTR': '季度',
            'Value': '金额',
            'Volume': '盒数',
            'Volume (Counting Unit)': '最小制剂单位数',
            '滚动年': 'MAT',
            '季度': 'QTR',
            '金额': 'Value',
            '盒数': 'Volume',
            '最小制剂单位数': 'Volume (Counting Unit)'
           }


# 左方表格数据获取
def get_distinct_list(column, db_table, ENGINE):
    sql = "Select DISTINCT " + column + " From " + db_table
    df = pd.read_sql_query(sql, ENGINE)
    l = df.values.flatten().tolist()
    return l

# sql语句初步拼接
def sqlparse(context, DB_TABLE):
    sql = "Select * from %s Where PERIOD = '%s' And UNIT = '%s'" % (
        DB_TABLE,
        context['PERIOD_select'][0],
        context['UNIT_select'][0]
    )  # context为前端通过表单传来的字典
    # 下面循环处理多选部分
    for k, v in context.items():
        if k not in ['csrfmiddlewaretoken', 'DIMENSION_select', 'PERIOD_select', 'UNIT_select']:
            if k[-2:] == '[]':
                field_name = k[:-9]  # 如果键以[]结尾，删除_select[]取原字段名
            else:
                field_name = k[:-7]  # 如果键不以[]结尾，删除_select取原字段名
            selected = v  # 选择项
            sql = sql_extent(sql, field_name, selected)  # 未来可以通过进一步拼接字符串动态扩展sql语句
    return sql


# 拼接字符串动态扩展sql语句
def sql_extent(sql, field_name, selected, operator=" AND "):
    if selected is not None:
        statement = ''
        for data in selected:
            statement = statement + "'" + data + "', "
        statement = statement[:-2]
        if statement != '':
            sql = sql + operator + field_name + " in (" + statement + ")"
    return sql


# 总体表现中市场当前表现的数据处理
def kpi(df):
    # 市场按列求和，最后一行（最后一个DATE）就是最新的市场规模
    market_size = df.sum(axis=1).iloc[-1]
    # 市场按列求和，倒数第5行（倒数第5个DATE）就是同比的市场规模，可以用来求同比增长率
    market_gr = df.sum(axis=1).iloc[-1] / df.sum(axis=1).iloc[-5] - 1

    # 因为数据第一年是四年前的同期季度，时间序列收尾相除后开四次方根可得到年复合增长率
    market_cagr = (df.sum(axis=1).iloc[-1] / df.sum(axis=1).iloc[0]) ** 0.25 - 1
    if market_size == np.inf or market_size == -np.inf:
        market_size = 'N/A'
    if market_gr == np.inf or market_gr == -np.inf:
        market_gr = 'N/A'
    if market_cagr == np.inf or market_cagr == -np.inf:
        market_cagr = 'N/A'

    return [market_size, "{0:.1%}".format(market_gr), market_cagr]


# 竞争现状列表数据获取
def ptable(df):
    # 份额
    df_share = df.transform(lambda x: x / x.sum(), axis=1)

    # 同比增长率，要考虑分子为0的问题
    df_gr = df.pct_change(periods=4)
    df_gr.dropna(how='all', inplace=True)
    df_gr.replace([np.inf, -np.inf], np.nan, inplace=True)

    # 最新滚动年绝对值表现及同比净增长
    df_latest = df.iloc[-1, :]
    df_latest_diff = df.iloc[-1, :] - df.iloc[-5, :]

    # 最新滚动年份额表现及同比份额净增长
    df_share_latest = df_share.iloc[-1, :]
    df_share_latest_diff = df_share.iloc[-1, :] - df_share.iloc[-5, :]

    # 进阶指标EI，衡量与市场增速的对比，高于100则为跑赢大盘
    df_gr_latest = df_gr.iloc[-1, :]
    df_total_gr_latest = df.sum(axis=1).iloc[-1] / df.sum(axis=1).iloc[-5] - 1
    df_ei_latest = (df_gr_latest + 1) / (df_total_gr_latest + 1) * 100

    df_combined = pd.concat(
        [df_latest, df_latest_diff, df_share_latest, df_share_latest_diff, df_gr_latest, df_ei_latest], axis=1)
    df_combined.columns = ['最新滚动年销售额',
                           '净增长',
                           '份额',
                           '份额同比变化',
                           '同比增长率',
                           'EI']

    return df_combined


# 竞争现状列表数据小数位处理
def build_formatters_by_cl(df):
    format_abs = lambda x: '{:,.0f}'.format(x)
    format_share = lambda x: '{:.2%}'.format(x)
    format_gr = lambda x: '{:.2%}'.format(x)
    format_currency = lambda x: '¥{:,.0f}'.format(x)
    d = {}
    for column in df.columns:
        if '份额' in column or '贡献' in column:
            d[column] = format_share
        elif '价格' in column or '单价' in column:
            d[column] = format_currency
        elif '同比增长' in column or '增长率' in column or 'CAGR' in column or '同比变化' in column:
            d[column] = format_gr
        else:
            d[column] = format_abs
    return d


# pivoted
def get_df(form_dict,ENGINE, is_pivoted=True):
    sql = sqlparse(form_dict,'chpa_data_test_dat')  # sql拼接
    df = pd.read_sql_query(sql, ENGINE)  # 将sql语句结果读取至Pandas Dataframe

    if is_pivoted is True:
        dimension_selected = form_dict['DIMENSION_select'][0]
        if dimension_selected[0] == '[':

            column = dimension_selected[1:][:-1]
        else:
            column = dimension_selected

        pivoted = pd.pivot_table(df,
                                 values='AMOUNT',  # 数据透视汇总值为AMOUNT字段，一般保持不变
                                 index='DATE',  # 数据透视行为DATE字段，一般保持不变
                                 columns=column,  # 数据透视列为前端选择的分析维度
                                 aggfunc=np.sum)  # 数据透视汇总方式为求和，一般保持不变
        if pivoted.empty is False:
            pivoted.sort_values(by=pivoted.index[-1], axis=1, ascending=False, inplace=True)  # 结果按照最后一个DATE表现排序

        return pivoted
    else:
        return df

