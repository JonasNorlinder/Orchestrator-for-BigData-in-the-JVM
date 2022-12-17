#!/usr/bin/python3

from typing import Dict, Final, List
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os
import unicodedata
import markdown
import textwrap
from shared.utils import has_key

class ReportVars:
  _instance = None
  def __new__(cls):
    if cls._instance is None:
      cls._instance = super(ReportVars, cls).__new__(cls)
    return cls._instance

  OP_RATE: Final[str] = "Op rate (op/s)"
  ROW_RATE: Final[str] = "Row rate (row/s)"
  LATENCY_MEAN: Final[str] = "Latency mean (ms)"
  LATENCY_MEDIAN: Final[str] = "Latency median (ms)"
  LATENCY_95: Final[str] = "Latency 95th percentile (ms)"
  LATENCY_99: Final[str] = "Latency 99th percentile (ms)"
  LATENCY_999: Final[str] = "Latency 99.9th percentile (ms)"
  LATENCY_MAX: Final[str] = "Latency max (ms)"
  TOTAL_GC_MINOR_COUNT: Final[str] = "Total minor GC count"
  TOTAL_GC_MAJOR_COUNT: Final[str] = "Total major GC count"

  column_names: Final[List[str]] = [OP_RATE, ROW_RATE, LATENCY_MEAN, LATENCY_MEDIAN, LATENCY_95, LATENCY_99, LATENCY_999, LATENCY_MAX, TOTAL_GC_MINOR_COUNT, TOTAL_GC_MAJOR_COUNT]
  types: Dict[str, str] = {
    OP_RATE: "float64",
    ROW_RATE: "float64",
    LATENCY_MEAN: "float64",
    LATENCY_MEDIAN: "float64",
    LATENCY_95: "float64",
    LATENCY_99: "float64",
    LATENCY_999: "float64",
    LATENCY_MAX: "float64",
    TOTAL_GC_MINOR_COUNT: "float64",
    TOTAL_GC_MAJOR_COUNT: "float64"
  }

  base_dir: Final[str] = os.path.join(os.path.dirname(os.path.realpath(__file__)), "results")
  threads: int = 0
  duration: int = 0
  data: Dict[str, pd.DataFrame] = dict()

ReportVars()


def format_columns(df) -> pd.DataFrame:
  df[ReportVars.LATENCY_MEAN] = df[ReportVars.LATENCY_MEAN].astype(float).map("{: .2f}".format)
  df[ReportVars.LATENCY_MEDIAN] = df[ReportVars.LATENCY_MEDIAN].astype(float).map("{: .2f}".format)
  df[ReportVars.LATENCY_95] = df[ReportVars.LATENCY_MEAN].astype(float).map("{: .2f}".format)
  df[ReportVars.LATENCY_99] = df[ReportVars.LATENCY_99].astype(float).map("{: .2f}".format)
  df[ReportVars.LATENCY_999] = df[ReportVars.LATENCY_999].astype(float).map("{: .2f}".format)
  df[ReportVars.LATENCY_MAX] = df[ReportVars.LATENCY_MAX].astype(float).map("{: .2f}".format)
  df[ReportVars.TOTAL_GC_MINOR_COUNT] = df[ReportVars.TOTAL_GC_MINOR_COUNT].astype(float).map("{: .0f}".format)
  df[ReportVars.TOTAL_GC_MAJOR_COUNT] = df[ReportVars.TOTAL_GC_MAJOR_COUNT].astype(float).map("{: .0f}".format)

  df[ReportVars.OP_RATE] = df[ReportVars.OP_RATE].astype(float).map("{: .0f}".format)
  df[ReportVars.ROW_RATE] = df[ReportVars.ROW_RATE].astype(float).map("{: .0f}".format)
  return df

def find_tags() -> List[str]:
  return next(os.walk(ReportVars.base_dir))[1]

def find_runs(tag: str) -> List[str]:
  return next(os.walk(os.path.join(ReportVars.base_dir, tag)))[1]

def get_dataframe(tag: str):
  if not has_key(ReportVars.data, tag):
    df = pd.DataFrame(columns=ReportVars.column_names)
    df = df.astype(dtype = ReportVars.types)
    df.name = tag
    ReportVars.data[tag] = df
  return ReportVars.data[tag]

def process_run(tag: str, run: str) -> None:
  df: pd.DataFrame = get_dataframe(tag)
  new_row = {
    ReportVars.OP_RATE: 0,
    ReportVars.ROW_RATE: 0,
    ReportVars.LATENCY_MEAN: 0.0,
    ReportVars.LATENCY_MEDIAN: 0.0,
    ReportVars.LATENCY_95: 0.0,
    ReportVars.LATENCY_99: 0.0,
    ReportVars.LATENCY_999: 0.0,
    ReportVars.LATENCY_MAX: 0.0,
    ReportVars.TOTAL_GC_MINOR_COUNT: 0,
    ReportVars.TOTAL_GC_MAJOR_COUNT: 0
  }
  global duration, threads
  with open(os.path.join(run, "client.log"), 'r') as readFile:
    float_check = [ReportVars.LATENCY_MEAN, ReportVars.LATENCY_MEDIAN, ReportVars.LATENCY_95, ReportVars.LATENCY_99, ReportVars.LATENCY_999, ReportVars.LATENCY_MAX]
    for line in readFile:
      if "threads" in line:
        ReportVars.threads = int(line.split("threads")[0].split("with ")[1])
        ReportVars.duration = int(line.split("threads")[1].split("minutes")[0])
        continue
      if "Op rate" in line:
        new_row[ReportVars.OP_RATE] = int(unicodedata.normalize("NFKD", line).split(':')[1].split('op/s')[0].replace(" ", "").replace(",", ""))
        continue
      if "Row rate" in line:
        new_row[ReportVars.ROW_RATE] = int(unicodedata.normalize("NFKD", line).split(':')[1].split('row/s')[0].replace(" ", "").replace(",", ""))
        continue
      for l in float_check:
        if l.split(" (ms)")[0] in line:
          new_row[l] = float(
            (unicodedata.normalize("NFKD", line).split(':')[1].split('ms')[0].replace(",", ""))
          )
          continue

    count_minor = 0
    count_major = 0
    with open(os.path.join(run, "client.gc"), 'r') as readFile:
      for line in readFile:
        if "[gc,start" in line:
          if "Major" in line:
            count_major += 1
          elif "Minor" in line:
            count_minor += 1
    new_row[ReportVars.TOTAL_GC_MINOR_COUNT] = count_minor
    new_row[ReportVars.TOTAL_GC_MAJOR_COUNT] = count_major

  df.loc[len(df)] = new_row

def produce_violin_plot(df, tags, path):
    fig, ax = plt.subplots()
    sub_df = df[tags]
    sns.violinplot(data=sub_df, orient='h', ax=ax)
    ax.set_yticklabels([textwrap.fill(e, 10) for e in list(sub_df.columns)])
    plt.tight_layout()
    name = ""
    for e in tags:
      name += e.replace(".", "_").replace("/", "_")
    file = os.path.join(path, name)
    ax.figure.savefig(file)
    return name + ".png"


def main() -> None:
  tags = find_tags()
  if len(tags) == 0:
    print("No data to process")
    exit(1)
  for tag in tags:
    runs = find_runs(tag)
    if len(runs) == 0:
      print(tag + " has no runs, skipping...")
      continue
    for run in runs:
      process_run(tag, os.path.join(ReportVars.base_dir, tag, run))

    df = get_dataframe(tag)

    files = list()
    for e in [[ReportVars.LATENCY_MEAN, ReportVars.LATENCY_MEDIAN],[ReportVars.LATENCY_95, ReportVars.LATENCY_99, ReportVars.LATENCY_999], [ReportVars.LATENCY_MAX], [ReportVars.OP_RATE], [ReportVars.ROW_RATE]]:
      files.append(produce_violin_plot(df, e, os.path.join(ReportVars.base_dir, tag)))
    print(files)
    with open(os.path.join(ReportVars.base_dir, tag, "summary.html"), "w") as writeFile:
      x = markdown.markdown(format_columns(df.describe()).to_markdown(), extensions=['markdown.extensions.tables'])
      writeFile.write("<h2>"+tag+"</h2>")
      writeFile.write(x)
      writeFile.write("<hr/>")
      writeFile.write("<h2>"+"Configuration"+"</h2>")
      writeFile.write("Client threads: " + str(ReportVars.threads) + "<br/>")
      writeFile.write("Duration: " + str(ReportVars.duration) + " minutes" +"<br/>")
      writeFile.write("<hr/>")
      writeFile.write("<h2>"+"Plots"+"</h2>")
      for e in files:
        writeFile.write("<img src=\"" + e + "\" />")

if __name__=="__main__":
  main()
