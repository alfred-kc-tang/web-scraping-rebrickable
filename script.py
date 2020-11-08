import collections
import http.client
import json
import sys
import time
import timeit

from pygexf.gexf import *

api_key = sys.argv[1]
api_header = "key " + api_key

start_time = timeit.default_timer()

connection = http.client.HTTPSConnection('rebrickable.com', 443, timeout = 10)

# Set the API parameters for geting the LEGO sets data.
sets_page = 1
sets_page_size = 301
sets_min_parts = 1130
sets_ordering = "num_parts"

# Request the sets data and extract a subset of results, i.e. set_num and name.
sets_url = "/api/v3/lego/sets/?page=" + str(sets_page) + "&page_size=" + str(
    sets_page_size) + "&min_parts=" + str(sets_min_parts) + "&ordering=" + "-"
    + sets_ordering
connection.request("GET", url = sets_url,
                   headers = {'Authorization': api_header})
response = connection.getresponse()
# print("Status: {} and reason: {}".format(response.status, response.reason))
lego_sets_raw = json.loads(response.read())["results"]
lego_sets_data = []

for i in range(len(lego_sets_raw)):
    lego_sets_filtered = dict((k,
        lego_sets_raw[i][k]) for k in ("set_num", "name"))
    lego_sets_filtered["set_name"] = lego_sets_filtered.pop("name")
    lego_sets_data.append(lego_sets_filtered)

# Set the API parameters for getting the LEGO parts data.
parts_page = 1
parts_page_size = 1000

# Request the parts data for each of the above selected sets, extract a subset
# of results, i.e. color, quantity, name, part_num, and create a unique id.
lego_parts_data = []
for i in range(len(lego_sets_data)):
    set_num = lego_sets_data[i]["set_num"]
    parts_url = "/api/v3/lego/sets/" + str(set_num) + "/parts/?page=" + str(
        parts_page) + "&page_size" + str(parts_page_size)
    connection.request("GET", url = parts_url,
                       headers = {'Authorization': api_header})
    response = connection.getresponse()
    # print("Status: {} and reason: {}".format(response.status, response.reason))
    lego_parts_raw = json.loads(response.read())["results"]
    lego_parts_sorted = sorted(lego_parts_raw, key = lambda k: k["quantity"],
                               reverse = True)

    if len(lego_parts_sorted) > 20:
        lego_parts_20 = lego_parts_sorted[:20]
    else:
        lego_parts_20 = lego_parts_sorted

    lego_parts_per_set = []
    for i in range(len(lego_parts_20)):
        d = {}
        d["part_color"] = lego_parts_20[i]["color"]["rgb"]
        d["part_quantity"] = lego_parts_20[i]["quantity"]
        d["part_name"] = lego_parts_20[i]["part"]["name"]
        d["part_num"] = lego_parts_20[i]["part"]["part_num"]
        d["part_id"] = d["part_num"] + "_" + d["part_color"]
        lego_parts_per_set.append(d)

    lego_parts_data.append(lego_parts_per_set)

# Close the HTTP connection.
connection.close()
# Check the time used.
print("The runtime for collecting Rebrickable Lego Data: ",
    timeit.default_timer() - start_time, " (seconds)")

# Construct a network graph using the pygexf library.
# Instantiate a static undirected graph and add the corresponding nodes & edges.
gexf = Gexf("Alfred Tang", "gexf file")
graph = gexf.addGraph("undirected", "static", "Lego Sets and Parts Graph")

type_attr = graph.addNodeAttribute(title = "Type", type = "string")

for i in range(len(lego_sets_data)):
    # Check whether there is an existing node with the id (i.e. set_num).
    if graph.nodeExists(id = lego_sets_data[i]["set_num"]) == 0:
        node = graph.addNode(id = lego_sets_data[i]["set_num"],
                             label = lego_sets_data[i]["set_name"],
                             r = "0", g = "0", b = "0")
        # Set attributes to perform partitioning operations within Gephi
        node.addAttribute(id = type_attr, value = "set")
    for j in range(len(lego_parts_data[i])):
        # Check whether there is an existing node with the id (i.e. part_id).
        if graph.nodeExists(id = lego_parts_data[i][j]["part_id"]) == 0:
            RGB_tup = tuple(int(lego_parts_data[i][j]["part_color"][k:k+2],
                16) for k in (0, 2, 4))
            node = graph.addNode(id = lego_parts_data[i][j]["part_id"],
                                 label = lego_parts_data[i][j]["part_name"],
                                 r = str(RGB_tup[0]), g = str(RGB_tup[1]),
                                 b = str(RGB_tup[2]))
            # Set attributes to perform partitioning operations within Gephi
            node.addAttribute(id = type_attr, value = "part")
        # Add an edge between each part and the set it belongs to, or the sets
        # it belongs to if it is used for more than one lego set.
        edge = graph.addEdge(
            id = lego_sets_data[i]["set_num"] + "_" + lego_parts_data[i][j][
                "part_id"],
            source = lego_sets_data[i]["set_num"],
            target = lego_parts_data[i][j]["part_id"],
            weight = lego_parts_data[i][j]["part_quantity"])

output_file = open("bricks_graph.gexf", "wb")
gexf.write(output_file)
output_file.close()

total_parts = 0
for i in range(len(lego_sets_data)):
    total_parts += len(lego_parts_data[i])
print("The total number of parts for all the selected sets: ", total_parts)