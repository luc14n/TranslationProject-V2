import matplotlib

matplotlib.use("Agg")
import os
from math import pi

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


class PipelineVisualizer:
    def __init__(self, output_dir="visualizations"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        sns.set_theme(style="whitegrid")
        # Brand colors for the "Royal Rumble"
        self.colors = {
            "OPENAI": "#1f77b4",  # Blue
            "GOOGLE_GEMINI": "#ff7f0e",  # Orange
            "ANTHROPIC_CLAUDE": "#9467bd",  # Purple
            "DEEPSEEK": "#d62728",  # Red
            "MOONSHOT_KIMI": "#2ca02c",  # Green
            "GLOBAL_AVG": "#7f7f7f",  # Grey
        }

    def normalize_comet(self, score):
        clipped = max(-1.0, min(1.0, score))
        return (clipped + 1.0) / 2.0

    def generate_radar_charts(self, dataset_name, provider_data):
        """Generates one radar chart per model, comparing it to the Global Dataset Average."""
        categories = ["LaBSE", "Fidelity", "BLEU", "COMET", "TTR"]
        N = len(categories)
        angles = [n / float(N) * 2 * pi for n in range(N)]
        angles += angles[:1]

        # Calculate Global Averages for this dataset
        all_l, all_f, all_b, all_c, all_t = [], [], [], [], []
        for p, s in provider_data.items():
            if not s["labse"]:
                continue
            all_l.append(np.mean(s["labse"]))
            all_f.append(np.mean(s["fidelity"]))
            all_b.append(np.mean(s["bleu"]) / 100.0)
            all_c.append(self.normalize_comet(np.mean(s["comet"])))
            all_t.append(np.mean(s["ttr"]))

        global_vals = [
            np.mean(all_l),
            np.mean(all_f),
            np.mean(all_b),
            np.mean(all_c),
            np.mean(all_t),
        ]
        global_vals += global_vals[:1]

        for provider, scores in provider_data.items():
            if not scores["labse"]:
                continue

            fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
            ax.set_theta_offset(pi / 2)
            ax.set_theta_direction(-1)
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(categories, fontsize=10, fontweight="bold")
            ax.set_ylim(0, 1)

            # Plot Global Avg (Reference)
            ax.plot(
                angles,
                global_vals,
                linewidth=1,
                linestyle="dashed",
                color=self.colors["GLOBAL_AVG"],
                label="Global Avg",
            )
            ax.fill(angles, global_vals, color=self.colors["GLOBAL_AVG"], alpha=0.1)

            # Plot Provider Avg
            p_vals = [
                np.mean(scores["labse"]),
                np.mean(scores["fidelity"]),
                np.mean(scores["bleu"]) / 100.0,
                self.normalize_comet(np.mean(scores["comet"])),
                np.mean(scores["ttr"]),
            ]
            p_vals += p_vals[:1]

            color = self.colors.get(provider, "#333333")
            ax.plot(angles, p_vals, linewidth=2, color=color, label=f"{provider} Avg")
            ax.fill(angles, p_vals, color=color, alpha=0.3)

            plt.title(
                f"{provider}: {dataset_name}\n(Semantic Footprint vs Global)",
                size=14,
                y=1.1,
                fontweight="bold",
            )
            plt.legend(loc="upper right", bbox_to_anchor=(1.2, 1.1))

            filename = os.path.join(
                self.output_dir, f"Radar_{dataset_name}_{provider}.png"
            )
            plt.savefig(filename, bbox_inches="tight", dpi=300)
            plt.close()

    def generate_judge_box_plot(self, all_judge_scores):
        """Creates the 'Qualitative Comparison' chart using Judge Scores across datasets."""
        # all_judge_scores structure: list of {'Provider': str, 'Score': float}
        df = pd.DataFrame(all_judge_scores)

        plt.figure(figsize=(10, 6))
        sns.boxplot(x="Provider", y="Score", data=df, palette=self.colors, width=0.4)
        sns.stripplot(
            x="Provider", y="Score", data=df, color=".3", size=5
        )  # Add individual dots

        plt.title(
            "Linguistic Integrity: Judge Score Distribution",
            fontsize=16,
            fontweight="bold",
        )
        plt.ylabel("Judge Score (%)")
        plt.ylim(0, 105)

        filename = os.path.join(self.output_dir, "Global_Judge_Comparison.png")
        plt.savefig(filename, bbox_inches="tight", dpi=300)
        plt.close()

    def generate_alignment_chart(self, dataset_name, provider_data):
        """Visualizes the 'Semantic Trajectory' (Degradation over Hops)."""
        records = []
        for provider, scores in provider_data.items():
            for i, score in enumerate(scores["comet"]):
                records.append({"Provider": provider, "Hop": i + 1, "COMET": score})

        df = pd.DataFrame(records)
        plt.figure(figsize=(12, 6))

        # Plot each model's decay line
        for provider in df["Provider"].unique():
            subset = df[df["Provider"] == provider]
            plt.plot(
                subset["Hop"],
                subset["COMET"],
                marker="o",
                label=provider,
                color=self.colors.get(provider, "#333333"),
                linewidth=2,
                markersize=7,
            )

        plt.title(
            f"Semantic Trajectory: {dataset_name}", fontsize=16, fontweight="bold"
        )
        plt.xlabel("Language Hop Number")
        plt.ylabel("COMET-QE (Translation Quality)")
        plt.xticks(
            range(1, 7),
            [
                "Hop 1\n(Germ)",
                "Hop 2\n(Rom)",
                "Hop 3\n(Slav)",
                "Hop 4\n(W.As)",
                "Hop 5\n(E.As)",
                "Hop 6\n(Eng)",
            ],
        )
        plt.axhline(0, color="black", linestyle="--", alpha=0.3)  # Baseline for quality
        plt.legend(title="Agents", bbox_to_anchor=(1.05, 1), loc="upper left")

        filename = os.path.join(self.output_dir, f"Alignment_{dataset_name}.png")
        plt.savefig(filename, bbox_inches="tight", dpi=300)
        plt.close()

    def render_all(self, dataset_name, provider_data, current_judge_scores):
        print(f"Rendering visualizations for {dataset_name}...")
        self.generate_radar_charts(dataset_name, provider_data)
        self.generate_alignment_chart(dataset_name, provider_data)
        # Note: The global box plot is usually rendered once after all datasets finish
