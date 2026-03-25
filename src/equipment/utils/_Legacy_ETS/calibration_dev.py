# import pandas as pd
import pandas as pd

# List1

db_1 = {
    400: -21,
    410: -22,
    420: -21,
    430: -19,
    440: -19.5,
    450: -19.21,
    460: -17.23
}

db_2 = {
    400: -23,
    410: -24,
    420: -25,
    430: -16,
    440: -18.5,
    450: -18.21,
    460: -17.23
}

db_3 = {
    400: -23,
    410: -24,
    420: -25,
    430: -16,
    440: -18.5,
    450: -18.21,
    460: -17.23
}

# lst = [['Geek', 25], ['is', 30],
#        ['for', 26], ['Geeksforgeeks', 22]]
#
# # creating df object with columns specified
# df = pd.DataFrame(lst, columns=['Tag', 'number'])
df = pd.DataFrame()
#df = pd.DataFrame.from_dict([db_1, db_2])
df = df.append(db_1, ignore_index=True)
df = df.append(db_2, ignore_index=True)
df = df.append(db_1, ignore_index=True)
df = df.append(db_1, ignore_index=True)
df = df.append(db_3, ignore_index=True)
df = df.append(db_3, ignore_index=True)
df = df.append(db_3, ignore_index=True)
df = df.append(db_1, ignore_index=True)
df = df.append(db_3, ignore_index=True)

print(df)