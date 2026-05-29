import sys, os
from pathlib import Path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.llm.deepanalyze_client import DeepAnalyzeClient

import pandas as pd
import sweetviz as sv
import plotly.express as px


def main():
	c = DeepAnalyzeClient()
	print('base_url=', c.base_url, 'model=', c.model)
	print('http root reachable:', c._http_check())
	print('models via http:', c._models_endpoint_check())
	print('models via cli:', c._local_cli_models())
	print('is_available:', c.is_available())

	# Look for a CSV in the workspace data folder
	workspace_root = Path(__file__).resolve().parents[2]
	csv_candidates = [
		workspace_root / 'data' / 'retail_mart_processed_v1.csv',
		workspace_root / 'data' / 'dataset.csv',
		# Backwards-compatible fallback if a user keeps the dataset at repo root
		workspace_root / 'retail_mart_processed_v1.csv',
	]
	csv_path = None
	for p in csv_candidates:
		if p.exists():
			csv_path = p
			break

	if not csv_path:
		print('No CSV dataset found at expected locations; skipping Sweetviz/Plotly report.')
		return

	print(f'Found dataset: {csv_path}')
	try:
		df = pd.read_csv(csv_path)
	except Exception as e:
		print('Failed to read CSV:', e)
		return

	# Generate Sweetviz report
	try:
		report = sv.analyze(df)
		out_html = workspace_root / 'deepanalyze_sweetviz_report.html'
		report.show_html(str(out_html))
		print('Sweetviz report written to', out_html)
	except Exception as e:
		print('Sweetviz report generation failed:', e)

	# Create a simple Plotly visualization for the first numeric column
	try:
		numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
		if numeric_cols:
			col = numeric_cols[0]
			fig = px.histogram(df, x=col, title=f'Histogram of {col}')
			out_plot = workspace_root / 'deepanalyze_plotly_histogram.html'
			fig.write_html(str(out_plot))
			print('Plotly histogram written to', out_plot)
		else:
			print('No numeric columns found for Plotly histogram.')
	except Exception as e:
		print('Plotly visualization failed:', e)


if __name__ == '__main__':
	main()
