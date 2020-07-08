# Analyse close stations within subways, find candidates for interchanges and suggest to confirm or not
# OBSOLETE SCRIPT - NO USE OF SQL NOW
from itertools import combinations
from get_distance import geo_distance


def route_interchanges_to_base(system_id, system_graph, cursor, db_connection):
    pairs = list(combinations(system_graph.nodes(), 2))
    i = 0
    total_steps = round(len(system_graph.nodes()) * len(system_graph.nodes()) / 2)
    for pair in pairs:
        transfer_max_length = 0.7  # assumption -> more than 700 m (10 min walk) significantly reduces amount of people wanting to transfer
        cursor.execute('''SELECT Station.id, Station.longitude, Station.latitude, Station.name,
            Route.ref, Route.type
            FROM Station JOIN Route JOIN RailwaySystem 
            ON Station.route_id = Route.id AND Route.system_id = RailwaySystem.id
            WHERE RailwaySystem.id = ? AND Station.id = ?
            LIMIT 1''', (system_id, pair[0]))
        station_from = cursor.fetchone()

        cursor.execute('''SELECT Station.id, Station.longitude, Station.latitude, Station.name,
            Route.ref, Route.type
            FROM Station JOIN Route JOIN RailwaySystem 
            ON Station.route_id = Route.id AND Route.system_id = RailwaySystem.id
            WHERE RailwaySystem.id = ? AND Station.id = ?
            LIMIT 1''', (system_id, pair[1]))
        station_to = cursor.fetchone()

        if (station_from[5] == 'tram' or station_from[5] == 'bus' or station_from[5] == 'trolleybus') and \
                (station_to[5] == 'tram' or station_to[5] == 'bus' or station_to[5] == 'trolleybus'):
            i += 1
            if i % 5000 == 0:
                print('Overall route-like interchange progress: ' + str(i) + '/' + str(total_steps) +
                      ' (' + str(round(i / total_steps * 100, 2)) + '%)')
                db_connection.commit()
            continue

        cursor.execute('SELECT * FROM Interchange WHERE station_id_from = ? AND station_id_to = ?',
                       (station_from[0], station_to[0]))
        one_way_exists = cursor.fetchone()
        cursor.execute('SELECT * FROM Interchange WHERE station_id_from = ? AND station_id_to = ?',
                       (station_to[0], station_from[0]))
        other_way_exists = cursor.fetchone()

        if one_way_exists or other_way_exists:
            i += 1
            if i % 5000 == 0:
                print('Overall route-like interchange progress: ' + str(i) + '/' + str(total_steps) +
                      ' (' + str(round(i / total_steps * 100, 2)) + '%)')
                db_connection.commit()
            continue

        distance = geo_distance(station_from[1], station_from[2], station_to[1], station_to[2])
        if distance <= transfer_max_length:
            interchange_from = str(station_from[3]) + ' (' + str(station_from[5]) + ', ' + str(station_from[4]) + ')'
            interchange_to = str(station_to[3]) + ' (' + str(station_to[5]) + ', ' + str(station_to[4]) + ')'
            interchange_name = interchange_from + ' <-> ' + interchange_to
            if interchange_from == interchange_to:
                decision = 'M'
                print(interchange_name + ', merging automatically...')
            elif (station_from[5] == 'tram' or station_from[5] == 'bus' or station_from[5] == 'trolleybus') or \
                    (station_to[5] == 'tram' or station_to[5] == 'bus' or station_to[5] == 'trolleybus'):
                decision = 'O'
                print(interchange_name + ', adding overground transfer automatically...')
            else:
                print(interchange_name + "? (R[regular]/O[overground]/X[crossplatform]/M[merge] or N[none]): ", end="")
                decision = input()
            if decision != 'N':
                cursor.execute('''INSERT INTO Interchange (name, station_id_from, station_id_to, length, type, system_id)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                               (
                                   interchange_name,
                                   station_from[0],
                                   station_to[0],
                                   distance,
                                   decision.upper(),
                                   system_id
                               )
                               )
        i += 1
        if i % 5000 == 0:
            print('Overall route-like interchange progress: ' + str(i) + '/' + str(total_steps) +
                  ' (' + str(round(i / total_steps * 100, 2)) + '%)')
            db_connection.commit()
    db_connection.commit()
    return True


def way_interchanges_to_base(system_id, system_graph, cursor, db_connection):
    pairs = list(combinations(system_graph.nodes(), 2))
    i = 0
    total_steps = round(len(system_graph.nodes()) * len(system_graph.nodes()) / 2)
    for pair in pairs:

        cursor.execute('SELECT * FROM Interchange WHERE station_id_from = ? AND station_id_to = ?',
                       (pair[0], pair[1]))
        one_way_exists = cursor.fetchone()
        cursor.execute('SELECT * FROM Interchange WHERE station_id_from = ? AND station_id_to = ?',
                       (pair[1], pair[0]))
        other_way_exists = cursor.fetchone()

        if one_way_exists or other_way_exists:
            i += 1
            if i % 5000 == 0:
                print('Overall way-like interchange progress: ' + str(i) + '/' + str(total_steps) +
                      ' (' + str(round(i / total_steps * 100, 2)) + '%)')
                db_connection.commit()
            continue

        transfer_max_length = 0.15  # assumption -> more than 150 m not relevant for overground transport
        cursor.execute('''SELECT Station.id, Station.longitude, Station.latitude, Station.name,
            Route.ref, Route.type
            FROM Station JOIN Route JOIN RailwaySystem 
            ON Station.route_id = Route.id AND Route.system_id = RailwaySystem.id
            WHERE RailwaySystem.id = ? AND Station.id = ?
            LIMIT 1''', (system_id, pair[0]))
        station_from = cursor.fetchone()

        cursor.execute('''SELECT Station.id, Station.longitude, Station.latitude, Station.name,
            Route.ref, Route.type
            FROM Station JOIN Route JOIN RailwaySystem 
            ON Station.route_id = Route.id AND Route.system_id = RailwaySystem.id
            WHERE RailwaySystem.id = ? AND Station.id = ?
            LIMIT 1''', (system_id, pair[1]))
        station_to = cursor.fetchone()

        distance = geo_distance(station_from[1], station_from[2], station_to[1], station_to[2])
        if distance <= transfer_max_length:
            interchange_from = str(station_from[3]) + ' (' + str(station_from[5]) + ', ' + str(station_from[4]) + ')'
            interchange_to = str(station_to[3]) + ' (' + str(station_to[5]) + ', ' + str(station_to[4]) + ')'
            interchange_name = interchange_from + ' <-> ' + interchange_to
            if interchange_from == interchange_to or station_from[3] == station_to[3] or distance == 0:
                decision = 'M'
                print(interchange_name + ', merging automatically...')
            elif station_from[5] != station_to[5]:
                decision = 'O'
                print(interchange_name + ', adding overground transfer automatically...')
            elif station_from[5] == station_to[5] and station_from[4] != station_to[4]:
                decision = 'O'
                print(interchange_name + ', adding overground transfer automatically...')
            else:
                decision = 'N'
            if decision != 'N':
                cursor.execute('''INSERT INTO Interchange (name, station_id_from, station_id_to, length, type, system_id)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                               (
                                   interchange_name,
                                   station_from[0],
                                   station_to[0],
                                   distance,
                                   decision.upper(),
                                   system_id
                               )
                               )
        i += 1
        if i % 5000 == 0:
            print('Overall way-like interchange progress: ' + str(i) + '/' + str(total_steps) +
                  ' (' + str(round(i / total_steps * 100, 2)) + '%)')
            db_connection.commit()
    db_connection.commit()
    return True


# more efficient script - but still OBSOLETE
def route_and_way_interchanges_to_base(system_id, system_graph, cursor, db_connection):
    pairs = list(combinations(system_graph.nodes(), 2))
    i = 0
    total_steps = round(len(system_graph.nodes()) * len(system_graph.nodes()) / 2)
    delayed_interchanges_to_add = list()
    for pair in pairs:

        cursor.execute('SELECT * FROM Interchange WHERE station_id_from = ? AND station_id_to = ?',
                       (pair[0], pair[1]))
        one_way_exists = cursor.fetchone()
        cursor.execute('SELECT * FROM Interchange WHERE station_id_from = ? AND station_id_to = ?',
                       (pair[1], pair[0]))
        other_way_exists = cursor.fetchone()

        if one_way_exists or other_way_exists:
            i += 1
            if i % 5000 == 0:
                print('Overall interchange progress: ' + str(i) + '/' + str(total_steps) +
                      ' (' + str(round(i / total_steps * 100, 2)) + '%)')
                db_connection.commit()
            continue

        transfer_max_length = 0.7  # assumption -> more than 700 m (10 min walk) significantly reduces amount of people wanting to transfer
        cursor.execute('''SELECT Station.id, Station.longitude, Station.latitude, Station.name,
            Route.ref, Route.type
            FROM Station JOIN Route JOIN RailwaySystem 
            ON Station.route_id = Route.id AND Route.system_id = RailwaySystem.id
            WHERE RailwaySystem.id = ? AND Station.id = ?
            LIMIT 1''', (system_id, pair[0]))
        station_from = cursor.fetchone()

        cursor.execute('''SELECT Station.id, Station.longitude, Station.latitude, Station.name,
            Route.ref, Route.type
            FROM Station JOIN Route JOIN RailwaySystem 
            ON Station.route_id = Route.id AND Route.system_id = RailwaySystem.id
            WHERE RailwaySystem.id = ? AND Station.id = ?
            LIMIT 1''', (system_id, pair[1]))
        station_to = cursor.fetchone()

        if (pair[0], pair[1]) == (7600, 7601) or (pair[0], pair[1]) == (7601, 7600):
            foo = 'bar'

        if (station_from[5] == 'tram' or station_from[5] == 'bus' or station_from[5] == 'trolleybus') and \
                (station_to[5] == 'tram' or station_to[5] == 'bus' or station_to[5] == 'trolleybus'):

            transfer_max_length = 0.15

            distance = geo_distance(station_from[1], station_from[2], station_to[1], station_to[2])
            if distance <= transfer_max_length:
                interchange_from = str(station_from[3]) + ' (' + str(station_from[5]) + ', ' + str(
                    station_from[4]) + ')'
                interchange_to = str(station_to[3]) + ' (' + str(station_to[5]) + ', ' + str(station_to[4]) + ')'
                interchange_name = interchange_from + ' <-> ' + interchange_to
                if interchange_from == interchange_to or station_from[3] == station_to[3] or distance == 0:
                    decision = 'M'
                    print(interchange_name + ', merging automatically...')
                elif station_from[5] != station_to[5]:
                    decision = 'O'
                    print(interchange_name + ', adding overground transfer automatically...')
                elif station_from[5] == station_to[5] and station_from[4] != station_to[4]:
                    decision = 'O'
                    print(interchange_name + ', adding overground transfer automatically...')
                else:
                    decision = 'N'
                if decision != 'N':
                    cursor.execute('''INSERT INTO Interchange (name, station_id_from, station_id_to, length, type, system_id)
                        VALUES (?, ?, ?, ?, ?, ?)''',
                                   (
                                       interchange_name,
                                       station_from[0],
                                       station_to[0],
                                       distance,
                                       decision.upper(),
                                       system_id
                                   )
                                   )
            i += 1
            if i % 5000 == 0:
                print('Overall interchange progress: ' + str(i) + '/' + str(total_steps) +
                      ' (' + str(round(i / total_steps * 100, 2)) + '%)')
                db_connection.commit()
        else:
            distance = geo_distance(station_from[1], station_from[2], station_to[1], station_to[2])
            if distance <= transfer_max_length:
                interchange_from = str(station_from[3]) + ' (' + str(station_from[5]) + ', ' + str(
                    station_from[4]) + ')'
                interchange_to = str(station_to[3]) + ' (' + str(station_to[5]) + ', ' + str(station_to[4]) + ')'
                interchange_name = interchange_from + ' <-> ' + interchange_to
                if interchange_from == interchange_to:
                    decision = 'M'
                    print(interchange_name + ', merging automatically...')
                elif (station_from[5] == 'tram' or station_from[5] == 'bus' or station_from[5] == 'trolleybus') or \
                        (station_to[5] == 'tram' or station_to[5] == 'bus' or station_to[5] == 'trolleybus'):
                    decision = 'O'
                    print(interchange_name + ', adding overground transfer automatically...')
                else:
                    delayed_interchanges_to_add.append((interchange_name,
                                                        station_from[0],
                                                        station_to[0],
                                                        distance,
                                                        system_id))
                    decision = 'N'
                if decision != 'N':
                    cursor.execute('''INSERT INTO Interchange (name, station_id_from, station_id_to, length, type, system_id)
                        VALUES (?, ?, ?, ?, ?, ?)''',
                                   (
                                       interchange_name,
                                       station_from[0],
                                       station_to[0],
                                       distance,
                                       decision.upper(),
                                       system_id
                                   )
                                   )
            i += 1
            if i % 5000 == 0:
                print('Overall interchange progress: ' + str(i) + '/' + str(total_steps) +
                      ' (' + str(round(i / total_steps * 100, 2)) + '%)')
                db_connection.commit()
    db_connection.commit()
    for interchange in delayed_interchanges_to_add:
        print(interchange[0] + "? (R[regular]/O[overground]/X[crossplatform]/M[merge] or N[none]): ",
              end="")
        decision = input()
        if decision != 'N':
            cursor.execute('''INSERT INTO Interchange (name, station_id_from, station_id_to, length, type, system_id)
                VALUES (?, ?, ?, ?, ?, ?)''',
                           (
                               interchange[0],
                               interchange[1],
                               interchange[2],
                               interchange[3],
                               decision.upper(),
                               interchange[4]
                           )
                           )
        db_connection.commit()
    return True
