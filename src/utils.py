import csv
import logging
import os
import pickle
from datetime import datetime
from functools import wraps
from math import cos, asin, sqrt

from base_station import BaseStation


def memorize(filename):
    """
    装饰器 保存函数运行结果
    :param filename: 缓存文件位置
    
    Example:
        @memorize('cache/square')
        def square(x):
            return x*x
            
    Todo:
        
    """

    def _memorize(func):
        @wraps(func)
        def memorized_function(*args, **kwargs):
            key = None
            if len(args) > 0:
                if isinstance(args[0], list):
                    key = len(args[0])
                else:
                    key = args[0]

            if os.path.exists(filename):
                with open(filename, 'rb') as f:
                    cached = pickle.load(f)
                    f.close()
                    if isinstance(cached, dict) and cached.get('key') == key:
                        logging.info(
                            msg='Found cache:{0}, {1} does not need to run'.format(filename, func.__name__))
                        return cached['value']

            value = func(*args, **kwargs)
            with open(filename, 'wb') as f:
                cached = {'key': key, 'value': value}
                pickle.dump(cached, f)
                f.close()
            return value

        return memorized_function

    return _memorize


class Utils(object):
    @staticmethod
    @memorize('cache/base_stations')
    def base_station_reader(path: str) -> [BaseStation]:
        """
        读取基站经纬度
        
        :param path: csv文件路径, 基站按地址排序
        :return: list of BaseStations
        """
        with open(path, 'r', ) as f:
            reader = csv.reader(f)
            base_stations = []
            count = 0
            for row in reader:
                address = row[0]
                latitude = float(row[1])
                longitude = float(row[2])
                base_stations.append(BaseStation(id=count, addr=address, lat=latitude, lng=longitude))
                logging.debug(
                    msg="(Base station:{0}:address={1}, latitude={2}, longitude={3})".format(count, address, latitude,
                                                                                             longitude))
                count += 1
            f.close()
            return base_stations

    @staticmethod
    @memorize('cache/base_stations_with_user_info')
    def user_info_reader(path: str, bs: [BaseStation]) -> [BaseStation]:
        """
        读取用户上网信息
        
        :param path: csv文件路径, 文件应按照基站地址排序
        :param bs: list of BaseStations
        :return: list of BaseStations with user info
        """
        with open(path, 'r') as f:
            reader = csv.reader(f)
            base_stations = []
            count = 0
            last_index = 0
            last_station = None  # type: BaseStation
            next(reader)  # 跳过标题
            for row in reader:
                address = row[4]
                s_begin_time = row[2]
                s_end_time = row[3]
                logging.debug(
                    msg="(User info::address={0}, begin_time={1}, end_time={2})".format(address, s_begin_time,
                                                                                        s_end_time))

                # 计算使用时间
                try:
                    begin_time = datetime.strptime(s_begin_time, r"%Y/%m/%d %H:%M")
                    end_time = datetime.strptime(s_end_time, r"%Y/%m/%d %H:%M")
                    minutes = (begin_time - end_time).seconds / 60
                except ValueError as ve:
                    logging.warning("Failed to convert time: " + str(ve))
                    minutes = 0

                if (not last_station) or (not address == last_station.address):
                    last_station = None
                    for i, item in enumerate(bs[last_index:]):
                        if address == item.address:
                            last_index = i
                            last_station = item
                            last_station.id = count
                            count += 1
                            base_stations.append(last_station)
                            break
                if last_station:
                    last_station.user_num += 1
                    last_station.workload += minutes
            f.close()
            return base_stations

    @staticmethod
    def _calc_distance(lat_a, lng_a, lat_b, lng_b):
        """
        由经纬度计算距离
        
        :param lat_a: 纬度A
        :param lng_a: 经度A
        :param lat_b: 纬度B
        :param lng_b: 经度B
        :return: 距离(km)
        """
        p = 0.017453292519943295  # Pi/180
        a = 0.5 - cos((lat_b - lat_a) * p) / 2 + cos(lat_a * p) * cos(lat_b * p) * (1 - cos((lng_b - lng_a) * p)) / 2
        return 12742 * asin(sqrt(a))  # 2*R*asin...

    @staticmethod
    @memorize('cache/distances')
    def distance_between_stations(base_stations: [BaseStation]) -> [[float]]:
        """
        计算基站之间的距离
        
        :param base_stations: list of BaseStation
        :return: 距离(km)
        """
        distances = []
        for i, station_a in enumerate(base_stations):
            distances.append([])
            for j, station_b in enumerate(base_stations):
                dist = _calc_distance(station_a.latitude, station_a.longitude, station_b.latitude, station_b.longitude)
                distances[i].append(dist)
            logging.debug("Calculated distance from {0} to other base stations".format(str(station_a)))
        return distances
