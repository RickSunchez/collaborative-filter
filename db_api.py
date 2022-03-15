import re
import sqlite3
import json
import os.path
import math
from sqlite3.dbapi2 import connect

sqrt = lambda x: math.sqrt(x)

# SOURCE: https://www.machinelearningmastery.ru/various-implementations-of-collaborative-filtering-100385c6dfe0/
compares = {
    "number": "=",
    "text": "LIKE",
    "json": "LIKE"
}
fields = {
    "id": {
        "col_name": "Идентификатор СТЕ",
        "type": "number"
    },
    "STE_name": {
        "col_name": "Наименование СТЕ",
        "type": "text"
    },
    "category": {
        "col_name": "Категория",
        "type": "text"
    },
    "description": {
        "col_name": "Описание",
        "type": "text"
    },
    "STE_properties": {
        "col_name": "Характеристики СТЕ",
        "type": "json"
    },
    "regions": {
        "col_name": "Регионы поставки",
        "type": "json"
    },
    "contract_count": {
        "col_name": "Кол-во заключенных контрактов",
        "type": "number"
    },
    "providers": {
        "col_name": "Поставщики",
        "type": "json"
    },
    "origin_country": {
        "col_name": "Страна происхождения",
        "type": "text"
    },
    "contract_anothers": {
        "col_name": "Другая продукция в контрактах",
        "type": "json"
    },
    "views": {
        "col_name": "Просмотры",
        "type": "number"
    },
    "KPGZ_id": {
        "col_name": "Идентификатор КПГЗ",
        "type": "number"
    },
    "KPGZ_code": {
        "col_name": "Код КПГЗ",
        "type": "text"
    },
    "model": {
        "col_name": "Модель",
        "type": "text"
    },
    "price": {
        "col_name": "Цена",
        "type": "json"
    }
}

class DB_interface:
    def __init__(self):
        self.db = sqlite3.connect("EKB_source.db", check_same_thread=False)
        # db.row_factory = sqlite3.Row
        self.cursor = self.db.cursor()

    def query(self, **kwargs):
        sql = "SELECT * FROM EKB_source WHERE "
        for key in kwargs:
            if key not in fields:
                return "KEY ERROR"
            else:
                t = "`%s` %s " % (
                    fields[key]["col_name"], 
                    compares[fields[key]["type"]]
                )

                if fields[key]["type"] == "number":
                    t += str(kwargs[key])
                else:
                    t += "'%s'" % str(kwargs[key])

                sql += t

        result = self.cursor.execute(sql + ";")
        return result.fetchall()

    def _get_regions(self):
        sql = """
            SELECT DISTINCT json_extract(value, "$.Name") as Region
            FROM `EKB_source`, json_each(json_extract(`EKB_source`.`Регионы поставки`, "$")) 
            ORDER BY Region ASC;
        """

        result = self.cursor.execute(sql)
        answer = []
        for row in result.fetchall():
            answer.append(row[0])

        with open("./db_dumps/regions.json", "w") as f:
            json.dump(answer, f)

        return True
    def get_regions(self):
        if not os.path.isfile("./db_dumps/regions.json"):
            self._get_regions()

        with open("./db_dumps/regions.json", "r") as f:
            data = json.load(f)

        return data

    def _get_categories(self):
        sql = """
            SELECT DISTINCT `Категория` as Category
            FROM `EKB_source`
            ORDER BY Category ASC
        """

        result = self.cursor.execute(sql)
        answer = []
        for row in result.fetchall():
            answer.append(row[0])

        with open("./db_dumps/categories.json", "w") as f:
            json.dump(answer, f)
        
        return True
    def get_categories(self):
        if not os.path.isfile("./db_dumps/categories.json"):
            self._get_categories()

        with open("./db_dumps/categories.json", "r") as f:
            data = json.load(f)

        return data

    def _get_positions_by_category(self, category, translit):
        sql = """
            SELECT *
            FROM `EKB_source`
            WHERE `Категория` LIKE "%s"
            ORDER BY `Наименование СТЕ` ASC
        """ % category

        result = self.cursor.execute(sql)

        answer = []
        for row in result.fetchall():
            answer.append({
                "id": row[0],
                "name": row[1]
            })

        with open("./db_dumps/%s.json" % translit, "w") as f:
            json.dump(answer, f)
        
        return True
    def get_positions_by_category(self, category, translit):
        f_name = "./db_dumps/%s.json" % translit
        
        if not os.path.isfile(f_name):
            self._get_positions_by_category(category, translit)

        with open(f_name, "r") as f:
            data = json.load(f)
            print(data)
        
        return data

    def create_new_user(self, name, region):
        sql = """
            INSERT INTO `users`
            VALUES (NULL, "%s", "%s", "", "", "")
        """ % (name, region)

        self.cursor.execute(sql)

        self.db.commit()

        sql = "SELECT `id` FROM `users` WHERE `id`=last_insert_rowid();"
        query = self.cursor.execute(sql)
        result = query.fetchall()

        userID = result[0][0]

        self.addUserToRating(userID)
        return True

    def get_users(self, ids=None):
        sql = "SELECT * FROM `users`"
        if ids != None:
            sql += " WHERE `id` IN (%s)" % ",".join(ids)

        result = self.cursor.execute(sql)
        answer = []

        for row in result.fetchall():
            answer.append({
                "id": row[0],
                "name": row[1],
                "region": row[2],
                "visited": row[3],
                "buyed": row[4],
                "basket": row[5],
            })

        return answer

    def addVisited(self, userID, posID):
        sql = """
            UPDATE users 
            SET visited  =  visited || ",%s" 
            WHERE id = %s""" % (str(posID), str(userID))

        self.cursor.execute(sql)
        self.db.commit()

    def addToBasket(self, userID, posID):
        sql = """
            UPDATE users 
            SET basket =  basket || ",%s" 
            WHERE id = %s
        """ % (str(posID), str(userID))

        self.cursor.execute(sql)
        self.db.commit()

    def kupi(self, userID):
        sql = "SELECT basket FROM users WHERE id = %s" % str(userID)
        query = self.cursor.execute(sql)
        result = query.fetchall()

        basket = result[0][0]
        poses = basket.split(",")[1:]

        for posID in poses:
            self.ratingIncrement(userID, posID)

        sql = """
            UPDATE users
            SET buyed = buyed || basket, basket = ""
            WHERE id = %s
        """ % str(userID)

        self.cursor.execute(sql)
        self.db.commit()

    def addUserToRating(self, userID):
        sql = "PRAGMA table_info(`rating`)"
        query = self.cursor.execute(sql)
        result = query.fetchall()

        to_insert = []
        for col in result:
            if col[1] == "userID":
                to_insert.append(userID)
            else:
                to_insert.append(0)

        to_insert = [str(i) for i in to_insert]
        sql = """
            INSERT INTO rating
            VALUES (%s)
        """ % ",".join(to_insert)

        self.cursor.execute(sql)
        self.db.commit()


    def ratingIncrement(self, userID, posID):
        sql = "PRAGMA table_info(`rating`);"

        query = self.cursor.execute(sql)
        result = query.fetchall()

        column_exist = False
        for row in result:
            if row[1] == str(posID):
                column_exist = True
                break
        
        if not column_exist:
            sql = """
                ALTER TABLE rating ADD COLUMN `%s` INTEGER DEFAULT 0 NOT NULL;
            """ % str(posID)
            self.cursor.execute(sql)

        sql = """
            SELECT * FROM `rating` WHERE `userID` = %s;
        """ % str(userID)
        query = self.cursor.execute(sql)
        result = query.fetchall()

        if len(result) == 0:
            sql = "PRAGMA table_info(`rating`)"
            query = self.cursor.execute(sql)
            result = query.fetchall()

            to_insert = []
            for col in result:
                if col[1] == "userID":
                    to_insert.append(userID)
                elif col[1] == str(posID):
                    to_insert.append(1)
                else:
                    to_insert.append(0)

            to_insert = [str(i) for i in to_insert]
            sql = """
                INSERT INTO rating
                VALUES (%s)
            """ % ",".join(to_insert)

            self.cursor.execute(sql)
        else:
            sql = """
                UPDATE rating SET `{0}` = `{0}` + 1 WHERE userID = {1}
            """.format(str(posID), str(userID))

            self.cursor.execute(sql)

        self.db.commit()

    # def collaborativeFilterByUser(self, userID):
    #     sql = "SELECT * FROM rating WHERE userID = %s" % str(userID)
    #     query = self.cursor.execute(sql)
    #     result = query.fetchall()

    #     ru1 = result[0][1:]

    #     sql = "SELECT * FROM rating WHERE userID != %s" % str(userID)
    #     query = self.cursor.execute(sql)
    #     result = query.fetchall()

    #     LENGTH = len(ru1)

    #     R2u1 = 0
    #     for r in ru1:
    #         R2u1 += r*r

    #     similars = []
    #     for row in result:
    #         ru2 = row[1:]

    #         R2u2 = 0
    #         for r in ru2:
    #             R2u2 += r*r

    #         cosSimilar = 0
    #         for i in range(LENGTH):
    #             t = sqrt(R2u1) * sqrt(R2u2)
    #             if t == 0:
    #                 t = 0.0000000000001
    #             cosSimilar += (ru1[i] * ru2[i]) / t

    #         similars.append({
    #             "userID": row[0],
    #             "sim": cosSimilar
    #         })

    #     similars = sorted(similars, key=lambda s: s["sim"])
    #     return {
    #         "for": userID,
    #         "similars": similars
    #     }

    def collaborativeFilterVectors(self, sourceVector=[], compareWith=[[],[]]):
        LENGTH = len(sourceVector)

        R2u1 = 0
        for r in sourceVector:
            R2u1 += r*r

        similars = []
        for row in compareWith:
            R2u2 = 0
            for r in row:
                R2u2 += r*r

            cosSimilar = 0
            for i in range(LENGTH):
                t = sqrt(R2u1) * sqrt(R2u2)
                if t == 0:
                    t = 0.0000000000001
                cosSimilar += (sourceVector[i] * row[i]) / t

            similars.append(cosSimilar)

        return similars

    def similarsUserBased(self, controlID):
        data = self.ratingTableWithBothTitles()
        data = data[1:]

        compareWithIDs = []

        compareWith = []
        control = None
        for row in data:
            if row[0] == controlID:
                control = row[1:]
            else:
                compareWithIDs.append(row[0])
                compareWith.append(row[1:])

        if control is None:
            return False

        similars = self.collaborativeFilterVectors(control, compareWith)

        answer = {
            "for": controlID,
            "val": []
        }

        for i in range(len(compareWithIDs)):
            answer["val"].append([compareWithIDs[i], similars[i]])

        return answer

    def similarsPositionBased(self, controlID):
        data = self.ratingTableWithBothTitles()
        data = self.T(data)[1:]

        compareWithIDs = []

        compareWith = []
        control = None
        for row in data:
            if row[0] == controlID:
                control = row[1:]
            else:
                compareWithIDs.append(row[0])
                compareWith.append(row[1:])

        if control is None:
            return False

        similars = self.collaborativeFilterVectors(control, compareWith)

        answer = {
            "for": controlID,
            "val": []
        }

        for i in range(len(compareWithIDs)):
            answer["val"].append([compareWithIDs[i], similars[i]])

        return answer

    def T(self, arr):
        result = []
        for i in range(len(arr[0])):
            row = []
            for j in range(len(arr)):
                row.append(arr[j][i])
            result.append(row)
        
        return result

    def ratingTableWithBothTitles(self):
        sql = "PRAGMA table_info(`rating`)"
        query = self.cursor.execute(sql)
        result = query.fetchall()

        posIDs = []
        for row in result:
            if row[1] != "userID":
                posIDs.append(int(row[1]))
            else:
                posIDs.append(row[1])

        sql = "SELECT * FROM `rating`"
        query = self.cursor.execute(sql)
        result = query.fetchall()

        table = [posIDs]
        for row in result:
            table.append(list(row))
        
        return table

    def recomendationsFor(self, userID):
        simUserLimit = 0.28
        lastUserCount = 5
        simLastLimit = 0.9
        lastLimitCount = 5
        answer = {
            "byRegion": [],
            "byUsers": [],
            "byPosition": [],
            "mostViewed": []
        }

        def onRepeats(insertedID):
            for key in answer:
                if insertedID in answer[key]:
                    return True
            return False
        
        similarsUsers = self.similarsUserBased(int(userID))
        
        similarsUsers["val"] = sorted(
            similarsUsers["val"],
            key=lambda s: s[1]
        )

        user = self.get_users(ids=[str(userID)])[0]

        sql = """
            SELECT * 
            FROM users 
            WHERE 
                id != %s 
            AND
                region = "%s"
        """ % (str(userID), user["region"])
        query = self.cursor.execute(sql)
        result = query.fetchall()

        byRegion = []
        for row in result:
            i = 0
            while i < len(similarsUsers["val"]):
                if similarsUsers["val"][i][0] == row[0]:
                    break
                i += 1

            if similarsUsers["val"][i][1] >= simUserLimit:
                simUser = self.get_users(ids=[str(similarsUsers["val"][i][0])])[0]
                positions = [int(i) for i in simUser["visited"].split(",")[1:]]

                if len(positions) > lastUserCount:
                    positions = positions[-lastUserCount:]

                for p in positions:
                    if not onRepeats(p):
                        answer["byRegion"].append(p)

            similarsUsers["val"].pop(i)

        for s in similarsUsers["val"]:
            if s[1] >= simUserLimit:
                simUser = self.get_users(ids=[str(s[0])])[0]

                positions = [int(i) for i in simUser["visited"].split(",")[1:]]

                if len(positions) > lastUserCount:
                    positions = positions[-lastUserCount:]

                for p in positions:
                    if not onRepeats(p):
                        answer["byUsers"].append(p)
        
        visited = [int(i) for i in user["visited"].split(",")[1:]]

        if len(visited) > lastLimitCount:
            visited = visited[-lastLimitCount:]

        for s in visited:
            similarsPosition = self.similarsPositionBased(s)
            similarsPosition["val"] = sorted(
                similarsPosition["val"],
                key=lambda s: s[1]
            )

            i = len(similarsPosition["val"])-1
            while i >= 0:
                sp = similarsPosition["val"][i][1]
                si = similarsPosition["val"][i][0]
                if sp >= simLastLimit and not onRepeats(si):
                    answer["byPosition"].append(si)
                else:
                    break
                i -= 1

        sql = """
            SELECT `Идентификатор СТЕ` 
            FROM `EKB_source` 
            ORDER BY  `Просмотры` ASC
            LIMIT 10
        """

        query = self.cursor.execute(sql)
        result = query.fetchall()

        for row in result:
            if row[0] not in answer["byPosition"] and not onRepeats(row[0]):
                answer["mostViewed"].append(row[0])
        
        return answer

    def getRecomendationData(self, userID):
        recomendations = self.recomendationsFor(userID)

        t = []
        counts = []
        for r in recomendations:
            t.extend(recomendations[r])
            counts.append(len(recomendations[r]))

        sql = """
            SELECT `Идентификатор СТЕ`, `Наименование СТЕ`, `Цена`
            FROM `EKB_source` 
            WHERE `Идентификатор СТЕ` IN (%s)
        """ % ",".join([str(i) for i in t])
        query = self.cursor.execute(sql)
        result = query.fetchall()

        self.db.commit()

        s = 0
        for key in recomendations:
            l = len(recomendations[key])
            recomendations[key] = []
            for i in range(s, s+l):
                recomendations[key].append({
                    "id": result[i][0],
                    "title": result[i][1],
                    "prices": result[i][2]
                })
            
            s = l

        return recomendations

    # Not tested
    def collaborativeFilterByPosition(self, posID):
        sql = "PRAGMA table_info(`rating`)"
        query = self.cursor.execute(sql)
        result = query.fetchall()

        posIDs = []
        for row in result:
            posIDs.append(row[1])
        
        sql = "SELECT `%s` FROM rating" % str(posID)
        query = self.cursor.execute(sql)
        result = query.fetchall()

        ru1 = []
        for row in result:
            ru1.append(row[0])

        LENGTH = len(result[0])

        R2u1 = 0
        for r in ru1:
            R2u1 += r*r

        sql = "SELECT * FROM rating"
        query = self.cursor.execute(sql)
        result = query.fetchall()

        similars = []

        for i in range(1, LENGTH):
            ru2 = []

            for j in range(len(result)):
                ru2 = result[j][i]
            
            R2u2 = 0
            for r in ru2:
                R2u2 += r*r

            cosSimilar = 0
            for i in range(LENGTH):
                cosSimilar += (ru1[i] * ru2[i]) / (sqrt(R2u1) * sqrt(R2u2))

            similars.append({
                "posID": posIDs[i],
                "sim": cosSimilar
            })
        
        similars = sorted(similars, key=lambda s: s["sim"])

        return {
            "for": posID,
            "similars": similars
        }

    # Not tested
    def normalizeCollaborativeByUsers(self, sims):
        normilize = {
            "for": sims["for"],
            "similars": []
        }

        sql = "SELECT * FROM rating WHERE userID != %s" % str(sims["for"])
        query = self.cursor.execute(sql)
        result = query.fetchall()

        simAbsSum = 0
        for s in sims["similars"]:
            simAbsSum += abs(s["sim"])

        for i in range(len(sims["similars"])):
            ru2 = []
            # Плохая штука, очень плохая штука
            for row in result:
                if row[0] == sims["similars"][i]["userID"]:
                    ru2 = row[1:]
                    break
            
            simSum = 0

            for r in ru2:
                simSum += sims["similars"][i]["sim"] * r

            normilize["similars"].append({
                "userID": sims["similars"][i]["userID"],
                "simN": simSum / simAbsSum
            })

        return normilize

    def DROP_RATINGS(self):
        sql = "DROP TABLE rating"
        self.cursor.execute(sql)

        sql = """
            CREATE TABLE "rating" (
	            "userID"	INTEGER
            );
        """
        self.cursor.execute(sql)

        self.db.commit()
    
    def CLEAR_USERS(self):
        sql = """
            UPDATE users 
            SET 
                visited = "",
                buyed = "",
                basket = ""
        """

        self.cursor.execute(sql)
        self.db.commit()

# test = DB_interface()

# print(test.similarsPositionBased(23007060))
# print(test.ratingTableWithBothTitles())
# print(test.collaborativeFilterByUser2(25, [12, 22]))
# print(test.collaborativeFilterByUser(25))
# test.kupi(14)
# test.DROP_RATINGS()
# test.CLEAR_USERS()
# print(test.similarsUserBased(1))

# a = test.getRecomendationData(1)
# print(a)
"""
SELECT *
FROM `EKB_source`, json_each(json_extract(`EKB_source`.`Регионы поставки`, "$")) AS  j
WHERE `EKB_source`.`Идентификатор СТЕ` = 20528973
AND j.value LIKE "%Москва%"
"""