import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import requests
import json
import threading
import time
import os
import logging
from dotenv import load_dotenv
from data_fetcher import EnergyDataFetcher
import threading
import time
from datetime import datetime
from typing import Dict, Any

# Load environment variables
load_dotenv()

# Custom color scheme
BG_COLOR = "#2B2B2B"
FG_COLOR = "#FFFFFF"
ACCENT_COLOR = "#5E81AC"  # Blue accent
PLOT_COLORS = ['#FFA500', '#00FF00', '#FF6B6B', '#4169E1']

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('energy_app.log'),
        logging.StreamHandler()
    ]
)

# Define energy sources with configurations
ENERGY_SOURCES = {
    'Solar': {
        'base_prod': 1000,
        'base_cost': 0.1,
        'color': '#FFA500'
    },
    'Wind': {
        'base_prod': 800,
        'base_cost': 0.08,
        'color': '#00FF00'
    },
    'Coal': {
        'base_prod': 500,
        'base_cost': 0.15,
        'color': '#FF6B6B'
    },
    'Natural Gas': {
        'base_prod': 600,
        'base_cost': 0.12,
        'color': '#4169E1'
    }
}

class EnergySource:
    def __init__(self, name, base_cost, capacity, cost_factors, icon_path):
        self.name = name
        self.base_cost = base_cost
        self.capacity = capacity
        self.cost_factors = cost_factors
        self.icon_path = icon_path  # Store the file path
        self.icon = None  # Will store the PhotoImage object later

class EnergyCalculator:
    def __init__(self):
        self.sources = []
        self.hourly_data = {}
        
    def add_source(self, source):
        self.sources.append(source)
    
    def calculate_hourly_costs(self):
        self.hourly_data = {hour: {'production': {}, 'cost': {}} for hour in range(24)}
        
        for hour in range(24):
            total_demand = 10000  # Example base demand (kW)
            demand_multiplier = 1 + 0.5 * np.sin((hour - 14) * np.pi/12)
            current_demand = total_demand * demand_multiplier
            
            for source in self.sources:
                time_factor = source.cost_factors.get(hour, 1.0)
                production = min(source.capacity, current_demand * 0.3)
                cost = source.base_cost * time_factor
                
                self.hourly_data[hour]['production'][source.name] = production
                self.hourly_data[hour]['cost'][source.name] = cost
                
                current_demand -= production
                if current_demand <= 0:
                    break

class EnergyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Smart Energy Analytics")
        self.geometry("1200x800")
        self.configure(bg=BG_COLOR)
        
        # Initialize components
        self.data_fetcher = EnergyDataFetcher()
        self.sources_data = {}
        self.update_interval = 300000  # 5 minutes in milliseconds
        
        # Create GUI elements
        self.create_widgets()
        
        # Initial data fetch
        self.start_realtime_updates()
    
    def create_widgets(self):
        # Main container
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(expand=True, fill='both', padx=20, pady=20)
        self.analysis_btn = ttk.Button(
        self.main_frame,
        text="Show Hourly Analysis",
        command=self.show_hourly_analysis
    )
        self.analysis_btn.pack(pady=5)
        
        # Create matplotlib figure
        self.figure = plt.Figure(figsize=(10, 8), facecolor=BG_COLOR)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.main_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # Create progress bar
        self.progress = ttk.Progressbar(self.main_frame, mode='determinate')
        self.progress.pack(fill='x', pady=10)
        
        # Create update button
        self.update_btn = ttk.Button(
            self.main_frame, 
            text="Fetch Latest Data", 
            command=self.start_realtime_updates
        )
        self.update_btn.pack(pady=5)
        
        # Add analysis button after update button
        self.analysis_btn = ttk.Button(
            self.main_frame,
            text="Show Hourly Analysis",
            command=self.show_hourly_analysis
        )
        self.analysis_btn.pack(pady=5)
    
    def start_realtime_updates(self):
        """Start background thread for real-time updates"""
        self.progress["value"] = 0
        self.progress.start(10)
        threading.Thread(target=self._update_loop, daemon=True).start()
    
    def _update_loop(self):
        """Background loop for fetching real-time data"""
        try:
            # Reset progress
            self.progress["value"] = 0
            progress_step = 100 / len(ENERGY_SOURCES)
            successful_fetches = 0
            
            # Fetch data for each source
            for source in ENERGY_SOURCES.keys():
                try:
                    logging.info(f"Fetching data for {source}...")
                    data = self.data_fetcher.fetch_realtime_data(source)
                    
                    if data and isinstance(data, dict) and self._validate_data(data):
                        self.sources_data[source] = data
                        successful_fetches += 1
                        logging.info(f"Successfully fetched and validated data for {source}")
                    else:
                        logging.error(f"Invalid or incomplete data for {source}")
                    
                    # Update progress
                    self.progress["value"] += progress_step
                    
                except Exception as e:
                    logging.error(f"Error fetching {source} data: {str(e)}")
                    continue
            
            # Update UI only if we have some valid data
            if successful_fetches > 0:
                self.after(0, self.update_display)
                if successful_fetches == len(ENERGY_SOURCES):
                    self.after(0, self.generate_recommendations)
            else:
                logging.error("No valid data available for display")
                self.after(0, lambda: messagebox.showerror(
                    "Error", 
                    "Failed to fetch energy data. Please check your connection and try again."
                ))
                
        except Exception as e:
            logging.error(f"Update loop error: {str(e)}")
        finally:
            self.progress.stop()
            self.progress["value"] = 100
            # Schedule next update
            self.after(self.update_interval, self.start_realtime_updates)
    
    def update_display(self):
        """Update the display with hourly data"""
        try:
            self.figure.clear()
            
            # Get current hour for x-axis
            current_hour = datetime.now().hour
            hours = [(current_hour - i) % 24 for i in range(24)]
            hours.reverse()  # Show oldest to newest
            
            # Create subplot layout
            gs = self.figure.add_gridspec(2, 1, height_ratios=[1, 1])
            
            # Production plot
            ax1 = self.figure.add_subplot(gs[0])
            ax1.set_facecolor(BG_COLOR)
            
            sources = list(self.sources_data.keys())
            
            # Plot production data
            for i, source in enumerate(sources):
                hourly_data = self.sources_data[source].get('hourly_production', {})
                productions = [hourly_data.get(h, 0) for h in hours]
                ax1.plot(hours, productions, marker='o', linestyle='-', 
                        label=source, color=PLOT_COLORS[i])
            
            ax1.set_title("24-Hour Energy Production", color=FG_COLOR, pad=10)
            ax1.set_xlabel("Hour", color=FG_COLOR)
            ax1.set_ylabel("MW", color=FG_COLOR)
            ax1.tick_params(colors=FG_COLOR)
            ax1.legend(facecolor=BG_COLOR, labelcolor=FG_COLOR)
            ax1.grid(True, alpha=0.2)
            
            # Format x-axis
            ax1.set_xticks(hours)
            ax1.set_xticklabels([f"{h:02d}:00" for h in hours], rotation=45)
            
            # Efficiency and cost plot
            ax2 = self.figure.add_subplot(gs[1])
            ax2.set_facecolor(BG_COLOR)
            
            for i, source in enumerate(sources):
                hourly_eff = self.sources_data[source].get('hourly_efficiency', {})
                hourly_cost = self.sources_data[source].get('hourly_cost', {})
                
                efficiencies = [hourly_eff.get(h, 0) * 100 for h in hours]
                costs = [hourly_cost.get(h, 0) for h in hours]
                
                # Plot efficiency
                ax2.plot(hours, efficiencies, marker='o', linestyle='-',
                        label=f'{source} Efficiency %', 
                        color=PLOT_COLORS[i], 
                        alpha=0.7)
                
                # Plot cost
                ax2.plot(hours, costs, marker='s', linestyle='--',
                        label=f'{source} Cost (€/kWh)', 
                        color=PLOT_COLORS[i], 
                        alpha=0.5)
            
            ax2.set_title("24-Hour Efficiency and Cost", color=FG_COLOR, pad=10)
            ax2.set_xlabel("Hour", color=FG_COLOR)
            ax2.tick_params(colors=FG_COLOR)
            ax2.legend(facecolor=BG_COLOR, labelcolor=FG_COLOR, ncol=2)
            ax2.grid(True, alpha=0.2)
            
            # Format x-axis
            ax2.set_xticks(hours)
            ax2.set_xticklabels([f"{h:02d}:00" for h in hours], rotation=45)
            
            # Adjust layout
            self.figure.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            logging.error(f"Error updating display: {str(e)}")
            messagebox.showerror("Error", "Failed to update display")
    
    def generate_recommendations(self):
        """Generate energy recommendations using DeepSeek LLM"""
        try:
            current_data = {
                source: data for source, data in self.sources_data.items()
            }
            
            # Format data for LLM
            analysis_text = f"""
            Current Energy Analysis ({datetime.now().strftime('%Y-%m-%d %H:%M')}):
            
            {'-'*50}
            Production Summary:
            """
            
            total_production = 0
            total_cost = 0
            
            for source, data in current_data.items():
                production = data.get('production', 0)
                cost = data.get('cost', 0)
                efficiency = data.get('efficiency', 0)
                
                total_production += production
                total_cost += production * cost
                
                analysis_text += f"""
                {source}:
                - Production: {production:.2f} MW
                - Cost: €{cost:.2f}/MWh
                - Efficiency: {efficiency*100:.1f}%
                """
            
            avg_cost = total_cost / total_production if total_production > 0 else 0
            analysis_text += f"""
            {'-'*50}
            Overall Metrics:
            - Total Production: {total_production:.2f} MW
            - Average Cost: €{avg_cost:.2f}/MWh
            """
            
            # Get LLM recommendations
            try:
                recommendations = self.data_fetcher.get_llm_recommendations(analysis_text)
                full_analysis = f"{analysis_text}\n\nAI Recommendations:\n{'-'*50}\n{recommendations}"
                self.show_recommendations(full_analysis)
                
            except Exception as e:
                logging.error(f"LLM API error: {str(e)}")
                self.show_recommendations(f"{analysis_text}\n\nAI Recommendations unavailable: {str(e)}")
                
        except Exception as e:
            logging.error(f"Error generating recommendations: {str(e)}")
            messagebox.showerror("Error", "Failed to generate recommendations")

    def show_recommendations(self, text):
        """Display recommendations in a window."""
        window = tk.Toplevel(self)
        window.title("AI Energy Analysis")
        window.geometry("800x600")
        window.configure(bg=BG_COLOR)
        
        # Add header
        header = ttk.Label(
            window,
            text="Smart Energy Recommendations",
            font=("Arial", 14, "bold"),
            foreground=FG_COLOR,
            background=BG_COLOR
        )
        header.pack(pady=10)
        
        # Improved text area
        text_area = scrolledtext.ScrolledText(
            window, 
            wrap=tk.WORD, 
            width=80, 
            height=30,
            bg=BG_COLOR,
            fg=FG_COLOR,
            font=("Arial", 11),
            padx=10,
            pady=10
        )
        text_area.insert(tk.END, text)
        text_area.pack(padx=20, pady=(0, 20), fill='both', expand=True)
        
        # Make text read-only
        text_area.configure(state='disabled')
        
        # Add save button
        save_btn = ttk.Button(
            window,
            text="Save Report",
            command=lambda: self.save_recommendations(text)
        )
        save_btn.pack(pady=(0, 10))

    def save_recommendations(self, text):
        """Save recommendations to a file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"energy_recommendations_{timestamp}.txt"
        
        try:
            with open(filename, 'w') as f:
                f.write(text)
            messagebox.showinfo("Success", f"Recommendations saved to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save recommendations: {str(e)}")

    def show_hourly_analysis(self):
        """Display hourly energy analysis"""
        try:
            analysis = self.data_fetcher.analyze_hourly_metrics()
            
            window = tk.Toplevel(self)
            window.title("Hourly Energy Analysis")
            window.geometry("900x700")
            window.configure(bg=BG_COLOR)
            
            # Header
            header = ttk.Label(
                window,
                text="Hourly Energy Analysis",
                font=("Arial", 14, "bold"),
                foreground=FG_COLOR,
                background=BG_COLOR
            )
            header.pack(pady=10)
            
            # Analysis text area
            text_area = scrolledtext.ScrolledText(
                window,
                wrap=tk.WORD,
                width=90,
                height=35,
                bg=BG_COLOR,
                fg=FG_COLOR,
                font=("Arial", 11)
            )
            text_area.insert(tk.END, analysis)
            text_area.pack(padx=20, pady=20)
            text_area.configure(state='disabled')
            
            # Save button
            save_btn = ttk.Button(
                window,
                text="Save Analysis",
                command=lambda: self.save_recommendations(analysis)
            )
            save_btn.pack(pady=(0, 10))
            
        except Exception as e:
            logging.error(f"Error showing hourly analysis: {str(e)}")
            messagebox.showerror("Error", "Failed to generate hourly analysis")

    def update_data(self):
        """Update energy data with better error handling and logging"""
        try:
            for source in ENERGY_SOURCES:
                logging.info(f"Fetching data for {source}...")
                data = self.data_fetcher.fetch_realtime_data(source)
                if data:
                    self.sources_data[source] = data
                    logging.info(f"Successfully updated data for {source}")
                else:
                    logging.error(f"Failed to get data for {source}")
            
            self.last_update = datetime.now()
            self.update_display()
            self.after(self.update_interval, self.update_data)
            
        except Exception as e:
            logging.error(f"Error in update loop: {str(e)}")
            self.after(self.update_interval, self.update_data)

    def _validate_data(self, data: Dict) -> bool:
        """Validate the structure of fetched data"""
        required_keys = ['production', 'efficiency', 'cost', 'hourly_production', 
                        'hourly_efficiency', 'hourly_cost']
        
        if not isinstance(data, dict):
            return False
            
        return all(key in data for key in required_keys)

if __name__ == "__main__":
    app = EnergyApp()
    app.mainloop()