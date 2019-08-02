import datetime
import pytz

Shanghai = pytz.timezone('Asia/Shanghai')
ImportantTimes = {
    'Patch_6_88':datetime.datetime(2016, 6, 12, 0, 0, 0, 0),
    'Patch_7_00':datetime.datetime(2016, 12, 13, 0, 0, 0, 0),
    'Patch_7_04':datetime.datetime(2017, 3, 15, 0, 0, 0, 0),
    'Patch_7_06':datetime.datetime(2017, 5, 15, 0, 0, 0, 0),
    'Kiev_Major':datetime.datetime(2017, 4, 22, 0, 0, 0, 0),
    'TI2017Qualifier':datetime.datetime(2017, 6, 26, 0, 0, 0, 0),
    'TI2017Group':datetime.datetime(2017, 8, 1, 0, 0, 0, 0),
    'Patch_7_07':datetime.datetime(2017, 11, 1, 0, 0, 0, 0),
    'MDLQual':datetime.datetime(2018, 3, 14, 0, 0, 0, 0),
    'BCampBerlin':datetime.datetime(2018, 3, 19, 0, 0, 0, 0),
    'PreviousMonth':datetime.datetime.today() - datetime.timedelta(days=30),
    'PreviousBiMonth': datetime.datetime.today() - datetime.timedelta(days=60),
    'PreviousTriMonth': datetime.datetime.today() - datetime.timedelta(days=95),
    'PreviousFortnight':datetime.datetime.today() - datetime.timedelta(days=14),
    'PreviousTriWeek':datetime.datetime.today() - datetime.timedelta(days=21),
    'Custom': datetime.datetime(2018, 5, 1, 0, 0, 0, 0),
    '2018': datetime.datetime(2018, 1, 1, 0, 0, 0, 0),
    'DreamLeague10': datetime.datetime(2018, 10, 29, 0, 0, 0, 0),
    'EpiBuildUp': datetime.datetime(2019, 4, 22, 0, 0, 0, 0),
    'Epi2019': datetime.datetime(2019, 6, 22, 0, 0, 0, 0),
    'TIQuals2019': datetime.datetime(2019, 7, 2, 0, 0, 0, 0),
    'TheSummit10': datetime.datetime(2019, 7, 25, 0, 0, 0, 0),
    'Ti2019Group': datetime.datetime(2019, 8, 15, 0, 0, 0, 0, tzinfo=Shanghai),
    'Ti2019Main': datetime.datetime(2019, 8, 20, 0, 0, 0, 0, tzinfo=Shanghai),
}