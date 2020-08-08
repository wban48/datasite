from django.shortcuts import render
from django.http import HttpResponse
from django.utils import six
from sqlalchemy import create_engine
import pandas as pd
import json
from .charts import *
from django.views.decorators.cache import cache_page  # 引用缓存装饰器
from django.contrib.auth.decorators import login_required  # @login_required装饰器
from io import BytesIO  # for modern python   # 输出格式为types

from io import StringIO  # for legacy python   # 输出格式为str
import datetime

# Create your views here.

ENGINE = create_engine('mysql://root:wbban48@localhost/CHPA_1806')

@login_required()
def index(request):
    # a = {'period_selected': 'MAT', 'unit_selected': 'Value', 'TCIII': 'C09C ANGIOTENS-II ANTAG, PLAIN|血管紧张素II拮抗剂，单一用药'}
    # sql = us_f.sqlparse(a, 'chpa_data_test_dat')  # 读取ARB市场的滚动年销售额数据
    # df = pd.read_sql_query(sql, ENGINE)  # 将sql语句结果读取至Pandas Dataframe
    # print(sql)

    mselect_dict = {}
    for key, value in D_list.items():
        mselect_dict[key] = {}
        mselect_dict[key]['select'] = value
        mselect_dict[key]['options'] = get_distinct_list(value, 'chpa_data_test_dat', ENGINE)

    context = {
        'mselect_dict': mselect_dict
    }

    return render(request, 'chpa_data/display.html', context=context)

@login_required()
def search(request, column, kw):
    # kw='%沙%'
    print(column)
    print(kw)
    print(request)
    sql = "SELECT DISTINCT %s FROM %s WHERE %s LIKE '%%%s%%'" % (column, 'chpa_data_test_dat', column, kw)
    # sql = "SELECT DISTINCT %s FROM %s WHERE %s LIKE " % (colmun, 'chpa_data_test_dat', colmun)  # 最简单的单一字符串like，返回不重复的前10个结果
    # sql=sql+"'"+kw+"'"

    df = pd.read_sql_query(sql, ENGINE)
    l = df.values.flatten().tolist()
    result_list = []
    for element in l:
        option_dict = {
            'name': element,
            'value': element
        }
        result_list.append(option_dict)

        res = {
            "success": True,
            "result": result_list,
            "code": 200
        }

    return HttpResponse(json.dumps(res, ensure_ascii=False), content_type="application/json charset=utf-8")


# @cache_page(60 * 60 * 24 * 30)  # 缓存30天
@login_required()
def query(request):
    form_dict = dict(six.iterlists(request.GET))
    pivoted = get_df(form_dict, ENGINE)

    table = ptable(pivoted)
    table = table.to_html(formatters=build_formatters_by_cl(table),  # 逐列调整表格内数字格式
                          classes='ui selectable celled table',  # 指定表格css class为Semantic UI主题
                          table_id='ptable'  # 指定表格id
                          )

    # Pyecharts交互图表
    bar_total_trend = json.loads(prepare_chart(pivoted, 'bar_total_trend', form_dict))
    # Matplotlib静态图表
    bubble_performance = prepare_chart(pivoted, 'bubble_performance', form_dict)

    context = {
        'market_size': kpi(pivoted)[0],
        'market_gr': kpi(pivoted)[1],
        'market_cagr': kpi(pivoted)[2],
        'ptable': table,
    }
    for v, k in context.items():
        # int64对象，json库不认识。
        if type(k) is not str:
            context[v] = k.astype(float)
    context['bar_total_trend'] = bar_total_trend
    context['bubble_performance'] = bubble_performance
    a = json.dumps(context, ensure_ascii=False)
    return HttpResponse(a,
                        content_type="application/json charset=utf-8")  # 返回结果必须是json格式





# 实现导出功能
@login_required()
def export(request, type, c):
    form_dict = dict(six.iterlists(request.GET))
    if type == 'pivot':
        df = get_df(form_dict, ENGINE)  # 透视后的数据
    else:
        df = get_df(form_dict, ENGINE, is_pivoted=False)  # 原始数

    if c == 'xlsx':
        # 导出数据为xlsx
        excel_file = BytesIO()
        last = '.xlsx'
        xlwriter = pd.ExcelWriter(excel_file, engine='xlsxwriter')

        df.to_excel(xlwriter, 'data', index=True)

        xlwriter.save()
        xlwriter.close()

    else:
        # 导出数据为csv
        excel_file = StringIO()
        last = '.csv'
        df = pd.DataFrame(df)
        print(df)
        df.to_csv(excel_file, index=True)
    excel_file.seek(0)

    # 设置浏览器mime类型
    response = HttpResponse(excel_file.read(),
                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    # 设置文件名
    now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")  # 当前精确时间不会重复，适合用来命名默认导出文件
    response['Content-Disposition'] = 'attachment; filename=' + now + last
    return response
