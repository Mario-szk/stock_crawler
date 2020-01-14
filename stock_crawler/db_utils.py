import traceback
from multiprocessing import Lock

from psycopg2 import errors
from psycopg2.pool import ThreadedConnectionPool


class DBUtils:
    __singleton = None
    __lock = Lock()

    QUOTES_UPSERT_SQL = f"""
            INSERT INTO quotes (NAME, CODE, OPENING_PRICE, LATEST_PRICE, QUOTE_CHANGE,
            CHANGE, VOLUME, TURNOVER, AMPLITUDE, TURNOVER_RATE, "PE_ratio", VOLUME_RATIO,
            MAX_PRICE, MIN_PRICE, CLOSING_PRICE, "PB_ratio", MARKET, TIME)
            VALUES 
            ({','.join(['%s'] * 18)})
            ON CONFLICT ON CONSTRAINT quotes_pkey
            DO UPDATE SET latest_price = excluded.latest_price,
                          change = excluded.change,
                          volume = excluded.volume,
                          turnover = excluded.turnover,
                          amplitude = excluded.amplitude,
                          turnover_rate = excluded.turnover_rate,
                          volume_ratio = excluded.volume_ratio,
                          max_price = excluded.max_price,
                          min_price = excluded.min_price
        """

    COMPANIES_UPSERT_SQL = f"""
            INSERT INTO companies (code, name, intro, manage, ssrq, clrq, fxl, fxfy, mgfxj, fxzsz,
            srkpj, srspj, srhsl, srzgj, djzql, wxpszql, mjzjje, zczb)
            VALUES 
            ({','.join(['%s'] * 18)})
            ON CONFLICT  ON CONSTRAINT companies_pkey
            DO UPDATE SET fxl = excluded.fxl,
                            fxfy = excluded.fxfy,
                            mgfxj = excluded.mgfxj,
                            fxzsz = excluded.fxzsz,
                            djzql = excluded.djzql,
                            wxpszql = excluded.wxpszql,
                            zczb = excluded.zczb
        """

    CODES_QUERY_SQL = f"""
        SELECT DISTINCT code FROM quotes
    """

    MANAGE_QUERY_SQL = f"""
        SELECT manage FROM companies order by code
    """

    def __init__(self, database_config):
        self.database_config = database_config
        pool_config = self.database_config['pool']
        conn_config = self.database_config['conn']
        self.conn_pool = ThreadedConnectionPool(minconn=pool_config['min'],
                                                maxconn=pool_config['max'],
                                                **conn_config)

    def closeall(self):
        self.conn_pool.closeall()

    def upsert_quotes(self, quotes):
        """更新行情"""
        conn = self.conn_pool.getconn()
        try:
            with conn.cursor() as cur:
                try:
                    cur.executemany(self.QUOTES_UPSERT_SQL, quotes)
                    conn.commit()
                except errors.UniqueViolation as e:
                    print("当前记录已存在")
                except errors.NotNullViolation as e:
                    print("违反非空约束")
        finally:
            self.conn_pool.putconn(conn)

    def upsert_company(self, company):
        """添加公司信息"""
        conn = self.conn_pool.getconn()
        try:
            value = [company['code'], company['name'], company['intro'], company['manage'],
                     company['ssrq'], company['clrq'], company['fxl'], company['fxfy'],
                     company['mgfxj'], company['fxzsz'], company['srkpj'], company['srspj'],
                     company['srhsl'], company['srzgj'], company['djzql'], company['wxpszql'],
                     company['mjzjje'], company['zczb']]
            with conn.cursor() as cur:
                cur.execute(self.COMPANIES_UPSERT_SQL, value)
                conn.commit()
        except errors.UniqueViolation as e:
            print("当前记录已存在")

        except errors.NotNullViolation as e:
            print("违反非空约束")
        finally:
            self.conn_pool.putconn(conn)

    def get_all_codes(self):
        """获得所有公司代码"""
        conn = self.conn_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(self.CODES_QUERY_SQL)
                codes = cur.fetchall()
            return codes
        except Exception as e:
            print(e)
        finally:
            self.conn_pool.putconn(conn)

    def get_all_manage(self):
        """获得所有公司经营范围"""
        conn = self.conn_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(self.MANAGE_QUERY_SQL)
                manage = cur.fetchall()
            return manage
        except Exception as e:
            print(e)
        finally:
            self.conn_pool.putconn(conn)

    @staticmethod
    def init(database_config):
        DBUtils.__lock.acquire()
        try:
            if DBUtils.__singleton is None:
                DBUtils.__singleton = DBUtils(database_config)
        except Exception:
            traceback.print_exc()
        finally:
            DBUtils.__lock.release()
        return DBUtils.__singleton