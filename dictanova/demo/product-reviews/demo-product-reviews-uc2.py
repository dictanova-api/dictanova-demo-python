# -*- coding: utf-8 -*-

"""
This script implements the second use case:
Measure the impact of the price on the score per product subcategory.
"""

import pandas as pd
import requests, json
import numpy as np
import sys

class DictanovaAPIAuth(requests.auth.AuthBase):
	"""Attaches Dictanova Bearer Authentication to the given Request object."""
	
	def __init__(self, id, secret):
		self.apiclient_id = id
		self.apiclient_secret = secret
		self._token = None
	
	def __eq__(self, other):
		return all([
			self.apiclient_id == getattr(other, 'apiclient_id', None),
			self.apiclient_secret == getattr(other, 'apiclient_secret', None)
		])
	
	def __ne__(self, other):
		return not self == other
	
	def __call__(self, r):
		r.headers['Authorization'] = self.get_token()
		return r
	
	def get_token(self):
		# Get authentication token
		if self._token is None:
			payload = {
				"clientId": self.apiclient_id,
				"clientSecret": self.apiclient_secret
			}
			r = requests.post("https://api.dictanova.io/v1/token", json=payload)
			self._token = r.json()
		# Always use the one in cache
		return "Bearer %s" % self._token["access_token"]

if __name__ == "__main__":
	# Prepare Auth handler with API client id and secret
	# https://docs.dictanova.io/docs/authentication-and-security
	clientId, clientSecret = open("../credentials", "r").readline().strip().split(";")
	dictanova_auth = DictanovaAPIAuth(clientId, clientSecret)
	
	####################################################################### AGGREGATION
	# Query for CSAT
	query = {
		"type" : "CSAT",
		"field" : "metadata.note_moyenne",
		"dimensions" : [
			{
				"field" : "metadata.subcategory",
				"group" : "DISTINCT"
			}
		]
	}
	print("Query:")
	print(json.dumps(query, indent=4, sort_keys=False))
	
	# Requests
	r_ref = requests.post(
		"https://api.dictanova.io/v1/aggregation/datasets/5b2286583a35940001399b1a/documents",
		json=query,
		auth=dictanova_auth)
	print(r_ref)
	query["query"] = {
		"field": "TERMS",
		"operator": "EQ",
		"value": "prix_NOUN",
		"opinion": "NEGATIVE"
	}
	r_neg = requests.post(
		"https://api.dictanova.io/v1/aggregation/datasets/5b2286583a35940001399b1a/documents",
		json=query,
		auth=dictanova_auth)
	print(r_neg)
	query["query"] = {
		"field": "TERMS",
		"operator": "EQ",
		"value": "prix_NOUN",
		"opinion": "POSITIVE"
	}
	r_pos = requests.post(
		"https://api.dictanova.io/v1/aggregation/datasets/5b2286583a35940001399b1a/documents",
		json=query,
		auth=dictanova_auth)
	print(r_pos)
	
	# Merge results
	merging = {
		"ref": pd.io.json.json_normalize(r_ref.json()["periods"][0]["values"]),
		"priceneg": pd.io.json.json_normalize(r_neg.json()["periods"][0]["values"]),
		"pricepos": pd.io.json.json_normalize(r_pos.json()["periods"][0]["values"])
	}
	# Flatten list of dimensions
	for df in merging.values():
		df["dimensions"] = df["dimensions"].apply(lambda x: x[0])
		df.set_index("dimensions", inplace=True)
	# Join
	merging["merged"] = merging["priceneg"].join(merging["pricepos"], 
		lsuffix="_priceneg", rsuffix="_pricepos")
	merging["merged"] = merging["merged"].join(merging["ref"])
	
	# Pretty print results and plot
	import matplotlib.pyplot as plt
	print("Impact of price on satisfaction score per product line")
	df = merging["merged"]
	df["var_if_pos"] = 100*(df["value_pricepos"] - df["value"]) / df["value"]
	df["var_if_neg"] = 100*(df["value_priceneg"] - df["value"]) / df["value"]
	print(df[["var_if_pos", "var_if_neg", "volume"]])
	df[["var_if_pos","var_if_neg"]].plot.bar(color=["seagreen","orangered"], rot=0)
	plt.show()

	