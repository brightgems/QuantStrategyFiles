# 导入聚宽函数库
import jqdata
from sqlalchemy import desc
import numpy as np
import pandas as pd
from dateutil import relativedelta
from sets import Set
import random 
import datetime as dt
import talib as tl
from datetime import datetime
from sets import Set
from jqdata import *

# 初始化函数，设定要操作的股票、基准等等
def initialize(context):
    # 定义一个全局变量, 保存要操作的股票
    # 000001(股票:平安银行)
    set_benchmark('000300.XSHG')
    run_daily(daily_operation,time='before_open')
    
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    g.repeat_days = 10
    g.count = 0
    g.update = False
    g.N = 8
    g.weight = 1/(float)(g.N)
    g.ma_lengths = [5,10, 20, 30]
    g.in_trend_days = 5
    g.Shanghai = []
    g.portofolio_value = []
    g.firstDay = True
    g.high_weight_stocks = ['601318.XSHG', '600036.XSHG','600016.XSHG', '601166.XSHG',
        '600000.XSHG', '600030.XSHG', '000002.XSHE', '600837.XSHG', '600519.XSHG', '000651.XSHE',
        '601328.XSHG', '600887.XSHG', '601288.XSHG', '601601.XSHG','601398.XSHG']
    g.MF_period = 3
    set_slip_fee(context)
    g.MACD_period = 90

def set_slip_fee(context):
    # 将滑点设置为0
    set_slippage(PriceRelatedSlippage(0.002))
    # 根据不同的时间段设置手续费
    dt=context.current_dt
    log.info(type(context.current_dt))
    
    if dt>datetime(2013,1, 1):
        set_commission(PerTrade(buy_cost=0.0003, sell_cost=0.0013, min_cost=5)) 
        
    elif dt>datetime(2011,1, 1):
        set_commission(PerTrade(buy_cost=0.001, sell_cost=0.002, min_cost=5))
            
    elif dt>datetime(2009,1, 1):
        set_commission(PerTrade(buy_cost=0.002, sell_cost=0.003, min_cost=5))
                
    else:
        set_commission(PerTrade(buy_cost=0.003, sell_cost=0.004, min_cost=5))




def daily_operation(context):
    #initialize_context_variable(context)
    market_risk_control_obj = market_risk_control()
    avoid_market_risk = market_risk_control_obj.avoid_market_rist_MF(g.high_weight_stocks,context)
    #avoid_market_risk = False
    if avoid_market_risk:
        context.selected_stocks = []
        g.update = True
        g.count == 0
        return
    
    if g.count == 0:
        candidates = list(get_all_securities(['stock']).index)
        process_stocks_obj = process_stocks(candidates)
        preprocessed_stocks = process_stocks_obj.get_proper_stocks(context)
        FFscore_module_obj = FFscore_module()
        good_stocks = FFscore_module_obj.calculate_FFScore(preprocessed_stocks)
        MACD_filerting_obj = MACD_filerting()
        good_stocks = MACD_filerting_obj.filter_by_MACD(good_stocks)
        #stock_risk_control_obj = stock_risk_control()
        #good_stocks = stock_risk_control_obj.get_in_trends(good_stocks,context)
        
        analyze_stock_based_on_pb_obj = analyze_stock_based_on_pb()
        stocksList = analyze_stock_based_on_pb_obj.ordered_by_pb_ratio(good_stocks)
        context.selected_stocks = stocksList[:g.N]
        g.count = g.count + 1
        g.update = True
    else:
        g.count = g.count + 1
        g.count = g.count% g.repeat_days
        g.update = False


class MACD_filerting():
    def __init__(self):
        pass
    
    def filter_by_MACD(self, stockList):
        price_df = self.get_close_prices_MACD(stockList)
        filerted_stockList = []
        for column in price_df:
            price_array = price_df[column].dropna()
            decline = self.MACD_sell(price_array.values)
            if not decline:
                filerted_stockList.append(column)
        return filerted_stockList
        
    def check_in_reverse_order(self,array_sample):
        for i in range(len(array_sample) - 1):
            #or abs((array_sample[i+1] -  array_sample[i])/array_sample[i]) < 0.1:
            if array_sample[i] <= array_sample[i+1] :
                return False
        return True
        
    def MACD_sell(self, close_prices_MACD_array,fastperiod=12, slowperiod=26, signalperiod=9):
        macdDIFF,macdDEA , hist = self.MACD_CN(close_prices_MACD_array, fastperiod, slowperiod, signalperiod) 
        for i in range(1,4):
            if math.isnan(hist[-i]):
                return False
        macdDIFF = macdDIFF[-3:]
        macdDEA = macdDEA[-3:]
        hist  = hist[-3:]
        if self.check_in_reverse_order(hist):
            return True
        return False
        
    def MACD_CN(self,close, fastperiod, slowperiod, signalperiod) :
    ##MA_Type: 0=SMA, 1=EMA, 2=WMA, 3=DEMA, 4=TEMA, 5=TRIMA, 6=KAMA, 7=MAMA, 8=T3 (Default=SMA)
        macdDIFF, macdDEA, macd = tl.MACDEXT(close, fastperiod=fastperiod, fastmatype=1, slowperiod=slowperiod, slowmatype=1, signalperiod=signalperiod, signalmatype=1)
        macd = macd * 2
        return macdDIFF , macdDEA, macd
        
    def get_close_prices_MACD(self,stockList) :
        #day_of_week = context.current_dt.weekday()
        price_df = history(g.MACD_period, unit='1d', field='close', security_list=stockList, df=True, skip_paused=False, fq='pre')
        return price_df
        
        
        
class market_risk_control():
    def __init__(self):
        return          
    
    def avoid_market_rist_MF(self,stock_list, context):
        delta = relativedelta.relativedelta(days=-1)
        dt = context.current_dt + delta
        money_df = get_money_flow(stock_list,  end_date=dt, fields=['net_amount_main', 'sec_code'], count= g.MF_period)
        money_series =  money_df['net_amount_main']
        print ('money dfis ', money_df)
        money_df.drop('sec_code',1, inplace=True)
        days_money_trend = []
        print ('money dfis ', money_df)
        for i in range(g.MF_period):
            days_money_trend.append(money_series.iloc[i::g.MF_period].sum())
        for money_flow in days_money_trend:
            if money_flow > 0:
                return False
        return True

class stock_risk_control():
    def __init__(self):
        pass
    
    def determine_significance_diff(self,sorted_mas, unsorted_mas) :
        violation_count = 0    
        for idx, val in enumerate(sorted_mas):
            if val != unsorted_mas[idx]:
                diff_pct = abs(val - unsorted_mas[idx])/min(val,unsorted_mas[idx])
                violation_count += 1   
                if diff_pct > 0.015 or violation_count > 1:
                    return True  
        return False
        
    def get_in_trends(self, available_stocks, context):
        # 建立需要移除的股票list，只要发现股票有两根均线不符合多头趋势，就加入删除名单并停止计算
        to_remove_list = []
    # 对于所有有效股票
        for security in available_stocks:
        # 获取最长ma长度
            longest_ma = max(g.ma_lengths)
        # 今日日期
            date = context.current_dt
            # 获取过去价格
            all_past_prices = attribute_history(security,longest_ma + g.in_trend_days -1, '1d', 'close',  skip_paused = True)
        # 对于认定趋势的每一天
            to_remove = True
            for day in range(g.in_trend_days):
            # 筛去尾部的-day天数据
                if day == 0:
                    past_prices = all_past_prices
                else:
                # df[:2] 取两行
                    past_prices = all_past_prices[:-day]
            # 建立空均线值list 
                mas = []
            # 对于所有均线长度
                for length in g.ma_lengths:
                # 截取相应数据
                    ma_data = past_prices[-length:]
                # 算均值
                    ma = sum(ma_data).iloc[0]/ length
                # 计入list 
                    mas.append(ma)
            # 从大到小排列均值list 
                sorted_mas = sorted(mas)
                #sorted_mas.reverse()
            # 如果排列之后和之前不
                if mas != sorted_mas:
                # 加入删除行列
                    if self.determine_significance_diff(sorted_mas, mas):
                        to_remove = False
                        break
            if to_remove:
                to_remove_list.append(security)
        for security in to_remove_list:
        # 就删了
            available_stocks.remove(security)
        return available_stocks
        
    
    
class process_stocks():
    def __init__(self, stockList):
        self.stockList = stockList
        pass
    
    def get_proper_stocks(self, context, deltaday = 800):
        
        def remove_unwanted_stocks():
            current_data = get_current_data()
            return [stock for stock in self.stockList 
                if not current_data[stock].is_st and (current_data[stock].name  is None or
                ( '*' not in current_data[stock].name 
                and '退' not in current_data[stock].name)) 
                and  not current_data[stock].paused]

        def fun_delNewShare(filtered_stocks):
            deltaDate = context.current_dt.date() - dt.timedelta(deltaday)
            tmpList = []
            for stock in filtered_stocks:
                if get_security_info(stock).start_date < deltaDate:
                    tmpList.append(stock)
            return tmpList
            
        unwanted_stocks = remove_unwanted_stocks()
        non_new_stocks = fun_delNewShare(unwanted_stocks)
        return non_new_stocks

class FFscore_module():
    def __init__(self):
        pass
    
    def split_df_based_on_statDate(self,df_current):
        statDateList = df_current['statDate']
        statDateSet = Set(statDateList)
        df_List = []
        for statDateDiff in statDateSet:
            df_List.append(df_current[df_current['statDate'] == statDateDiff])
        return df_List
        
    def find_fundamentalInformation_last_two_years(self, df_current,last_statYear_query_time, last_twoYear_query_time, month_of_year, stockList):
        q = query(balance.code, indicator.roe,  income.operating_revenue, balance.total_assets, balance.total_current_assets,\
            balance.total_non_current_liability, balance.total_non_current_assets, balance.statDate).filter(valuation.code.in_(stockList)) 
        
        df_lastYear = get_fundamentals(q,statDate=str(last_statYear_query_time)+month_of_year)
        df_lastYear_index_array =  df_lastYear['code'].values
        df_lastYear.index = df_lastYear['code'].values
            
        df_lastSecond_year = get_fundamentals(q,statDate=str(last_twoYear_query_time)+month_of_year)
        df_lastSecond_year_index_array =  df_lastSecond_year['code'].values
        df_lastSecond_year.index = df_lastSecond_year['code'].values
        
        stock_index_intersection = np.intersect1d(df_lastSecond_year_index_array,df_lastYear_index_array, stockList)
        df_lastYear = df_lastYear.ix[stock_index_intersection]
        df_lastSecond_year = df_lastSecond_year.ix[stock_index_intersection]
        df_current = df_current.ix[stock_index_intersection]
        
        df_lastYear.index = df_lastYear['code'].values
        df_lastSecond_year.index = df_lastSecond_year['code'].values
        
        last_year_null_index = df_lastYear[pd.isnull(df_lastYear).any(1) == True].index
        lastSecond_year_null_index = df_lastSecond_year[pd.isnull(df_lastSecond_year).any(1) == True].index
        
        
        if len(last_year_null_index) != 0:
            df_lastYear.dropna(inplace=True)
            df_current.drop(last_year_null_index,errors='ignore',inplace=True)
            df_lastSecond_year.drop(last_year_null_index,errors='ignore',inplace=True)
            
        if len(lastSecond_year_null_index) != 0:
            df_lastSecond_year.dropna(inplace=True)
            df_lastYear.drop(lastSecond_year_null_index,errors='ignore',inplace=True)
            df_current.drop(lastSecond_year_null_index,errors='ignore',inplace=True)
            
        if len(df_lastYear) != len(df_current) or len(df_lastYear) != len(df_lastSecond_year):
            log.error('wrong length !!!!!!!!!!!!!' )
            exit()
            
        return df_current,df_lastYear,df_lastSecond_year
        
        
    def calculate_FFScore_For_stockList(self, df_current, last_statYear_query_time,last_twoYear_query_time, month_of_year, stockList):
        
        
        df_current,df_lastYear,df_lastSecond_year = self.find_fundamentalInformation_last_two_years(df_current, \
                last_statYear_query_time, last_twoYear_query_time, month_of_year, stockList)
        print ('df_current is ', len(df_current))
        zzscore_df = pd.DataFrame(index=df_current.index, columns=['A','B','C','D','E','sum'])
        print ('zzscore_df is ', len(zzscore_df))
        ###########    asset turnover
        asset_turnover_valueAfter = df_current['operating_revenue']/(0.5*df_current['total_assets'] + 0.5*df_lastYear['total_assets'])
        asset_turnover_valueBefore = df_lastYear['operating_revenue']/(0.5*df_lastYear['total_assets'] + 0.5*df_lastSecond_year['total_assets'])
        stock_index_total_asset_Good = df_current[asset_turnover_valueAfter > asset_turnover_valueBefore].index
        stock_index_total_asset_Bad =  df_current[asset_turnover_valueAfter <= asset_turnover_valueBefore].index
        zzscore_df['A'][stock_index_total_asset_Good] = 1
        zzscore_df['A'][stock_index_total_asset_Bad] = 0
        
        
        ############## current asset turnover
        Current_asset_turnover_after = df_current['operating_revenue']/(0.5*df_current['total_current_assets'] + 0.5*df_lastYear['total_current_assets'])
        Current_asset_turnover_before = df_lastYear['operating_revenue']/(0.5*df_lastYear['total_current_assets'] + 0.5*df_lastSecond_year['total_current_assets'])
        stock_index_current_asset_Good = df_current[Current_asset_turnover_after > Current_asset_turnover_before].index
        stock_index_current_asset_Bad =  df_current[Current_asset_turnover_after <= Current_asset_turnover_before].index
        zzscore_df['B'][stock_index_current_asset_Good] = 1
        zzscore_df['B'][stock_index_current_asset_Bad] = 0
    
        ############## lever 
        total_non_current_liability_current_year = df_current['total_non_current_liability']
        total_non_current_liability_last_year = df_lastYear['total_non_current_liability']
        total_non_current_liability_two_year = df_lastSecond_year['total_non_current_liability']
        total_non_current_assets_current_year = df_current['total_non_current_assets']
        total_non_current_assets_last_year = df_lastYear['total_non_current_assets']
        total_non_current_assets_two_year = df_lastSecond_year['total_non_current_assets']
        lever_after = ((total_non_current_liability_last_year + total_non_current_liability_current_year)/2)/(0.5*total_non_current_assets_current_year + \
            0.5*total_non_current_assets_last_year)
        lever_before =  ((total_non_current_liability_last_year + total_non_current_liability_two_year)/2)/(0.5*total_non_current_assets_last_year + \
            0.5*total_non_current_assets_two_year)
        stock_index_lever_Bad = df_current[lever_after > lever_before].index
        stock_index_lever_Good = df_current[lever_after <= lever_before].index
        zzscore_df['C'][stock_index_lever_Good] = 1
        zzscore_df['C'][stock_index_lever_Bad] = 0
        
        
        ############### current year roe
        roe_series_after = df_current['roe']
        roe_series_before = df_lastYear['roe']
        roe_series_good = df_current[roe_series_after > 0].index
        roe_series_bad = df_current[roe_series_after <= 0].index
        zzscore_df['D'][roe_series_good] = 1
        zzscore_df['D'][roe_series_bad] = 0
        
        ############### delta roe
        roe_series_delta_good = df_current[roe_series_after > roe_series_before].index
        roe_series_delta_bad = df_current[roe_series_after <= roe_series_before].index
        zzscore_df['E'][roe_series_delta_good] = 1
        zzscore_df['E'][roe_series_delta_bad] = 0
        score_series = zzscore_df.sum(axis=1)
        score_series.sort(ascending=False)
        print ('the score is ',score_series[0])
        return score_series
        
        
    def calculate_FFScore(self,stockList):
        q = query(balance.code, indicator.roe,income.operating_revenue, balance.total_assets, balance.total_current_assets,\
        balance.total_non_current_liability, balance.total_non_current_assets, balance.statDate).filter(valuation.code.in_(stockList))
        df_current = get_fundamentals(q)
        df_current.index = df_current['code'].values
        df_current = df_current.drop('code',1)
        #df_current_null_index = df_current[pd.isnull(df_current).any(1) == True].index
        df_current.dropna(inplace=True)
        #pass_in_stocks = list(df_current.index)
        
        print ('df_current length is ', len(df_current))
        
        df_List = self.split_df_based_on_statDate(df_current)
        good_stocks = []
        for df in df_List:
            statDateFormat = df['statDate'][0]
            datetime_object = datetime.strptime(statDateFormat, '%Y-%m-%d')
            last_statYear_query_time = datetime_object.year - 1
            last_twoYear_query_time = datetime_object.year - 2
            if datetime_object.month == 3:
                month_of_year = 'q1'
            elif datetime_object.month == 6:
                month_of_year = 'q2'
            elif datetime_object.month == 9:
                month_of_year = 'q3'
            else:
                month_of_year = 'q4'
            pass_in_stocks = list(df.index)

            score_series = self.calculate_FFScore_For_stockList(df,\
                   last_statYear_query_time,last_twoYear_query_time,month_of_year,pass_in_stocks)
            good_stocks = good_stocks + list(score_series[score_series == 5].index)
        
        return good_stocks
        
            
    
class analyze_stock_based_on_pb():
    def __init__(self):
        pass
    
    def ordered_by_pb_ratio(self, stockList):
        q = query(valuation.pb_ratio, valuation.code).filter(valuation.code.in_(stockList)).order_by(
            valuation.pb_ratio)
        df = get_fundamentals(q)
        df.index = df['code'].values
        stocks = list(df['code'].values)
        print df.head()['pb_ratio']
        return stocks
        
def after_trading_end(context):
    
    if not g.firstDay:
        shanghai_df = attribute_history('000001.XSHG', 1, unit='1d',\
            fields=['close'],\
            skip_paused=True, df=True, fq='pre')
        g.Shanghai.append(shanghai_df['close'][0])
        
    else:
        g.firstDay = False
    g.portofolio_value.append(context.portfolio.portfolio_value)
    print ('the coeffient ratio is ', np.corrcoef(g.Shanghai, g.portofolio_value[:-1])[0][1])
# 每个单位时间(如果按天回测,则每天调用一次,如果按分钟,则每分钟调用一次)调用一次
def handle_data(context, data):
    if g.update :
        update_position(context,data)

def update_position(context, data):
    def sell_stock():
        for p in context.portfolio.positions:
            if p not in context.selected_stocks :
                o = order_target(p, 0)
            
    def buy_stock():
        target_value = g.weight * context.portfolio.portfolio_value
        for s in context.selected_stocks:
            o = order_target_value(s, target_value)
        
    message_sell = sell_stock()
    message_buy = buy_stock()
    
    
        
        
        