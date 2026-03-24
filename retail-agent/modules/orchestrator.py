from modules.data_loader import DataLoader
from modules.eda_agent import EDAAgent
from modules.explainer import Explainer
from modules.preprocessor import Preprocessor
from modules.report_generator import ReportGenerator


class Orchestrator:
    def __init__(self, csv_path, user_query, target_col=None, llm_model="retail-analyst"):
        self.csv_path = csv_path
        self.user_query = user_query
        self.target_col = target_col
        self.llm_model = llm_model

        self.data = None
        self.preprocessed = None
        self.eda_results = None
        self.explanations = None
        self.report = None

    def run(self):
        """Execute the full pipeline."""
        print("Loading data...")
        loader = DataLoader(self.csv_path)
        self.data = loader.load()

        print("Preprocessing...")
        pre = Preprocessor(self.data)
        self.preprocessed = pre.run()
        pre_report = pre.get_report()

        print("Running EDA...")
        eda = EDAAgent(self.preprocessed)
        self.eda_results = eda.run()
        plots = eda.generate_plots()

        print("Generating explainable insights...")
        explainer = Explainer(
            self.preprocessed,
            target_col=self.target_col,
            llm_model=self.llm_model,
        )
        self.explanations = explainer.explain_features(query_context=self.user_query)

        print("Creating report...")
        report_generator = ReportGenerator(
            user_query=self.user_query,
            eda_results=self.eda_results,
            explanations=self.explanations,
            preprocessing_report=pre_report,
            plots=plots,
            llm_model=self.llm_model,
        )
        self.report = report_generator.generate_markdown()

        print("Analysis complete.")
        return self.report
