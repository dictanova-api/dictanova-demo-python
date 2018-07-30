# -*- coding: utf-8 -*-

"""
UC#01: Identify top 10 criteria spontaneously discussed by customers and that have 
the most impact on the satisfaction score
"""

import pandas as pd
import requests, json, sys
import numpy as np
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from matplotlib import colors

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
	
	####################################################################### TOP OPINION
	# Request for top 100 opinions
	top100_opinions = []
	for page in range(1,3):
		r = requests.post(
			"https://api.dictanova.io/v1/search/datasets/5b55b264dbcd8100019f0495/terms",
			data="", # empty query
			params={"page": page, "pageSize": 50}, # https://docs.dictanova.io/docs/pagination
			auth=dictanova_auth)
		print(r)
		top100_opinions += r.json()["items"]

	############################################################## COMPUTE REFERENCE CSAT
	# Compute the distribution of the CSAT that will serve as reference to compute impact
	query = {
		"type" : "COUNT",
		"field" : "metadata.rating_satisfaction",
		"dimensions" : [
			{
				"field" : "metadata.rating_satisfaction",
				"group": "DISTINCT"
			}
		]
	}
	# Request
	r = requests.post(
		"https://api.dictanova.io/v1/aggregation/datasets/5b55b264dbcd8100019f0495/documents",
		json=query,
		auth=dictanova_auth)
	print(r)
	ref_distr = {int(v["dimensions"][0]): v["value"] for v in r.json()["periods"][0]["values"]}
	ref_total = r.json()["periods"][0]["total"]["value"]
	# Pretty print
	print("Reference distribution of CSAT for rating_satisfaction:")
	ref_sum = 0
	for i in range(1,6):
		print("\t%d/5 => %d documents (%0.1f%%)" % (i, ref_distr[i], 100.*ref_distr[i]/ref_total))
		ref_sum += i*ref_distr[i]
	ref_csat = 1.*ref_sum/ref_total
	print("Reference CSAT on perimeter: %0.2f" % ref_csat)
	
	# init the computation matrix
	ref_distr.update({"opinion": "__REF__", "base": ref_total})
	df_impact = pd.DataFrame.from_records([ref_distr])
	
	##################################################################### MEASURE IMPACT
	# Compute the impact of each opinion on the score rating_satisfaction
	for opinion in top100_opinions:
		print("Fetching data to measure impact of '%s' on rating_satisfaction" % opinion["label"])
		query = {
			"type" : "COUNT",
			"field" : "metadata.rating_satisfaction",
			"query": {
				"field": "TERMS",
				"operator": "EQ",
				"value": opinion["id"]
			},
			"dimensions" : [
				{
					"field" : "metadata.rating_satisfaction",
					"group": "DISTINCT"
				}
			]
		}
		# Request
		r = requests.post(
			"https://api.dictanova.io/v1/aggregation/datasets/5b55b264dbcd8100019f0495/documents",
			json=query,
			auth=dictanova_auth)
		print(r)
		# Add data
		opinion_distr = {int(v["dimensions"][0]): v["value"] for v in r.json()["periods"][0]["values"]}
		opinion_distr.update({
				"opinion": opinion["id"], 
				"lbl": opinion["label"],
				"base": r.json()["periods"][0]["total"]["value"]
			})
		df_impact = df_impact.append(pd.DataFrame.from_records([opinion_distr]), ignore_index=True)
	
	# Now compute the impact of each opinion with various method
	for note in range(1,6):
		df_impact["%d_weight" % note] = note * df_impact[note]
	df_impact["sum_regular"] = df_impact[["5_weight","4_weight","3_weight","2_weight","1_weight"]].sum(axis="columns")
	
	# Simple average
	df_impact["csat_regular"] = 1. * df_impact["sum_regular"] / df_impact["base"]
	df_ref = df_impact[ df_impact["opinion"] == "__REF__" ]
	df_impact["var_csat_regular"] = df_impact["csat_regular"] - df_ref["csat_regular"][0]
	
	# Neutralize this opinion
	df_impact["sum_without"] = df_ref["sum_regular"][0] - df_impact["sum_regular"]
	df_impact["base_without"] = df_ref["base"][0] - df_impact["base"]
	df_impact["csat_without"] = 1. * df_impact["sum_without"] / df_impact["base_without"]
	df_impact["var_csat_without"] = df_impact["csat_without"] - df_ref["csat_regular"][0]
	
	# Neutralize unsatisfied (<4/5) with this opinion
	df_impact["sum_unsat"] = df_impact[["3_weight","2_weight","1_weight"]].sum(axis="columns")
	df_impact["vol_unsat"] = df_impact[[3,2,1]].sum(axis="columns")
	df_impact["csat_rm_unsat"] = (1. * df_impact["sum_regular"] - df_impact["sum_unsat"]) / (df_impact["base"] - df_impact["vol_unsat"])
	df_impact["var_csat_rm_unsat"] = df_impact["csat_rm_unsat"] - df_ref["csat_regular"][0]
	
	# Neutralize satisfied (>3/5) with this opinion
	df_impact["sum_sat"] = df_impact[["5_weight","4_weight"]].sum(axis="columns")
	df_impact["vol_sat"] = df_impact[[5,4]].sum(axis="columns")
	df_impact["csat_rm_sat"] = (1. * df_impact["sum_regular"] - df_impact["sum_sat"]) / (df_impact["base"] - df_impact["vol_sat"])
	df_impact["var_csat_rm_sat"] = df_impact["csat_rm_sat"] - df_ref["csat_regular"][0]
	
	##################################################################### DISPLAY RESULTS
	
	# Remove __REF__ for generating tops
	dfops = df_impact[df_impact["opinion"] != "__REF__"]

	wcp = WordCloud(
		prefer_horizontal=1, background_color="white", 
		colormap=colors.ListedColormap(['seagreen']))
	wcn = WordCloud(
		prefer_horizontal=1, background_color="white", 
		colormap=colors.ListedColormap(['orangered']))
	wcm = WordCloud(
		prefer_horizontal=1, background_color="white", 
		colormap=colors.ListedColormap(['gold']))

	print("[Regular] Top 10 opinions with best satisfaction:")
	dfops.sort_values("var_csat_regular", ascending=False, inplace=True)
	# Display as table
	print(dfops.iloc[0:10][["opinion","var_csat_regular","csat_regular","base"]])
	# Display as wordcloud
	wcp.fit_words({r.lbl:r.var_csat_regular for r in dfops.iloc[:50].itertuples()})
	plt.title("[Regular] Top opinions with best satisfaction")
	plt.imshow(wcp)
	plt.axis("off")
	#plt.show()
	plt.savefig("uc1-top100-best-satisfaction.png", bbox_inches='tight')
	# plt.close() # https://github.com/matplotlib/matplotlib/issues/9856/
	
	print("[Regular] Top 10 opinions with worst satisfaction:")
	dfops.sort_values("var_csat_regular", ascending=True, inplace=True)
	# Display as table
	print(dfops.iloc[0:10][["opinion","var_csat_regular","csat_regular","base"]])
	# Display as wordcloud
	wcn.fit_words({r.lbl:r.var_csat_regular*-1 for r in dfops.iloc[:50].itertuples()})
	plt.title("[Regular] Top opinions with worst satisfaction")
	plt.imshow(wcn)
	plt.axis("off")
	#plt.show()
	plt.savefig("uc1-top100-worst-satisfaction.png", bbox_inches='tight')
	# plt.close() # https://github.com/matplotlib/matplotlib/issues/9856/
	
	print("[Impact without] Top 10 opinions that weight positively on satisfaction:")
	dfops.sort_values("var_csat_without", ascending=True, inplace=True)
	# Display as table
	print(dfops.iloc[0:10][["opinion","var_csat_without","csat_without","base"]])
	# Display as wordcloud
	wcp.fit_words({r.lbl:r.var_csat_without*-1 for r in dfops.iloc[:50].itertuples()})
	plt.title("[Impact without] Top opinions that weight positively on satisfaction")
	plt.imshow(wcp)
	plt.axis("off")
	#plt.show()
	plt.savefig("uc1-top100-weights-positively.png", bbox_inches='tight')
	# plt.close() # https://github.com/matplotlib/matplotlib/issues/9856/
	
	print("[Impact without] Top 10 opinions that weight negatively on satisfaction:")
	dfops.sort_values("var_csat_without", ascending=False, inplace=True)
	# Display as table
	print(dfops.iloc[0:10][["opinion","var_csat_without","csat_without","base"]])
	# Display as wordcloud
	wcn.fit_words({r.lbl:r.var_csat_without for r in dfops.iloc[:50].itertuples()})
	plt.title("[Impact without] Top opinions that weight negatively on satisfaction")
	plt.imshow(wcn)
	plt.axis("off")
	#plt.show()
	plt.savefig("uc1-top100-weights-negatively.png", bbox_inches='tight')
	#plt.close() # https://github.com/matplotlib/matplotlib/issues/9856/

	print("[Satisfied Impact] Top 10 opinions that should be preserved to maintain satisfaction:")
	dfops.sort_values("var_csat_rm_sat", ascending=True, inplace=True)
	# Display as table
	print(dfops.iloc[0:10][["opinion","var_csat_rm_sat","csat_rm_sat","base"]])
	# Display as wordcloud
	wcp.fit_words({r.lbl:r.var_csat_rm_sat*-1 for r in dfops.iloc[:50].itertuples()})
	plt.title("[Satisfied Impact] Top opinions that should be preserved to maintain satisfaction")
	plt.imshow(wcp)
	plt.axis("off")
	#plt.show()
	plt.savefig("uc1-top100-to-maintain.png", bbox_inches='tight')
	# plt.close() # https://github.com/matplotlib/matplotlib/issues/9856/
	
	print("[Unsatisfied Impact] Top 10 opinions that can be leveraged to improve satisfaction:")
	dfops.sort_values("var_csat_rm_unsat", ascending=True, inplace=True)
	# Display as table
	print(dfops.iloc[0:10][["opinion","var_csat_rm_unsat","var_csat_rm_unsat","base"]])
	# Display as wordcloud
	wcn.fit_words({r.lbl:r.var_csat_rm_sat for r in dfops.iloc[:50].itertuples()})
	plt.title("[Unsatisfied Impact] Top opinions that can be leveraged to improve satisfaction")
	plt.imshow(wcn)
	plt.axis("off")
	#plt.show()
	plt.savefig("uc1-top100-to-leverage.png", bbox_inches='tight')
	#plt.close() # https://github.com/matplotlib/matplotlib/issues/9856/
	
	