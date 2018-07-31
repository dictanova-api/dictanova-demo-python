# -*- coding: utf-8 -*-

"""
UC#03 : Trending opinions
Identify trending opnions for a particular period
"""

import pandas as pd
import requests, json, re, sys
import numpy as np

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
	
	############################################################## TOP OPINION PER PERIOD
	# Request for top opinions over a period (S14 to S22 in 2015)
	query = {
		"type" : "COUNT",
		"field" : "createdAt",
		"query" : {
			"operator": "AND",
			"criteria": [
				# Between S14
				{
					"field": "metadata.date_of_purchase",
					"operator": "GTE",
					"value": "2015-03-30T00:00:00Z"
				}, 
				# and S22
				{
					"field": "metadata.date_of_purchase",
					"operator": "LTE",
					"value": "2015-05-31T23:59:59Z"
				}
			]
		},
		"dimensions" : [{
				"field": "metadata.date_of_purchase",
				"group": "WEEK"
			}, {
				"field" : "TERMS",
				"group": "DISTINCT",
				"limit": 100
			}, {
				"field" : "TERMS_POLARITY",
				"group": "DISTINCT"
			}
		]
	}
	r = requests.post(
		"https://api.dictanova.io/v1/aggregation/datasets/5b55b264dbcd8100019f0495/documents",
		json=query,
		auth=dictanova_auth)
	print(r)
	
	####################################################################### PREPARE DATA
	
	# Load in pandas
	df = pd.io.json.json_normalize(r.json()["periods"][0]["values"])
	df["week"] = df["dimensions"].apply(lambda x: x[0])
	df["opinion"] = df["dimensions"].apply(lambda x: x[1])
	df["polarity"] = df["dimensions"].apply(lambda x: x[2])
	df.drop(columns=["dimensions", "volume"], inplace=True)
	df = df.pivot_table(index=["opinion", "week"], columns="polarity", values="value")
	df.rename(columns={
		"POSITIVE": "pos",
		"NEGATIVE": "neg",
		"NEUTRAL": "neu"
	}, inplace=True)
	df.fillna(value=0, inplace=True)
	
	# Keep only significative data (occ over week > 10)
	df["all"] = df[["pos","neg","neu"]].sum(axis="columns")
	df = df[df["all"]>10]
	
	################################################################## DISPLAY TRENDS 1
	# Trending is a very subjective quality of the data, it can be implemented in 
	# various ways. For the sake of this example, we will consider as trending opinions
	# which frequencies are strongly increasing in positive and negative polarity.
	# By strongly increasing we mean more than 1 std compared to the last 4 periods
	print("Trending = positive / negative frequency increases more than 1 std")
	for week in range(18, 23):
		# Prepare the week range that serve as reference
		wrange = ["2015-W%d"%i for i in range(week-4, week)]
		# Compute the mean and std of each opinion over the period before the last 
		# week we are interested in
		df_mean = df.iloc[df.index.get_level_values('week').isin(wrange)].mean(axis="index", level=0)
		df_std = df.iloc[df.index.get_level_values('week').isin(wrange)].std(axis="index", level=0)
		# Compute variation in std
		df_var_std = (df.iloc[df.index.get_level_values('week')=="2015-W%d"%week] - df_mean) / df_std
		
		# Select the top 5 trends positive and negative after filtering the significative
		# variations only
		top5_neg = df_var_std[df_var_std["neg"]>1].sort_values("neg", ascending=False).iloc[:5]
		top5_pos = df_var_std[df_var_std["pos"]>1].sort_values("pos", ascending=False).iloc[:5]
		
		# Display
		print("=== 2015-W%d ==" % week)
		print("  Trending negative opinions:")
		for trend in top5_neg.itertuples():
			print("\t%s" % trend.Index[0])
		print("  Trending positive opinions:")
		for trend in top5_pos.itertuples():
			print("\t%s" % trend.Index[0])
	
	################################################################## DISPLAY TRENDS 2
	# In this example, we will consider as trending opinions the opinions which 
	# frequencies are increasing as a whole (positive, negative and neutral) by more 
	# than 1 std compared to the last 4 periods.
	print("Trending = global frequency increases more than 1 std")
	for week in range(18, 23):
		# Prepare the week range that serve as reference
		wrange = ["2015-W%d"%i for i in range(week-4, week)]
		# Compute the mean and std of each opinion over the period before the last 
		# week we are interested in
		df_mean = df.iloc[df.index.get_level_values('week').isin(wrange)].mean(axis="index", level=0)
		df_std = df.iloc[df.index.get_level_values('week').isin(wrange)].std(axis="index", level=0)
		# Compute variation in std
		df_var_std = (df.iloc[df.index.get_level_values('week')=="2015-W%d"%week] - df_mean) / df_std
		
		# Select the top 5 trends as global variation
		top5_all = df_var_std[df_var_std["all"]>1].sort_values("all", ascending=False).iloc[:5]
		
		# Display
		print("=== 2015-W%d ==" % week)
		print("  Trending opinions:")
		for trend in top5_all.itertuples():
			print("\t%s" % trend.Index[0])
	