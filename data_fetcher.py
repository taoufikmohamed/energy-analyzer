from typing import Dict, Any
import requests
import logging
import time
from datetime import datetime
import os
from dotenv import load_dotenv
from constants import (
    EIA_ENDPOINT,
    DEEPSEEK_ENDPOINT,
    CONNECT_TIMEOUT,
    READ_TIMEOUT,
    ENERGY_SOURCES
)

class EnergyDataFetcher:
    def __init__(self):
        load_dotenv()
        
        # Initialize API keys
        self.api_key = os.getenv('ENERGY_API_KEY')
        if not self.api_key:
            raise ValueError("ENERGY_API_KEY not found in environment")
        
        # Configure session
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            max_retries=3,
            pool_connections=10,
            pool_maxsize=10
        )
        self.session.mount('https://', adapter)
        
        # Set headers
        self.eia_headers = {
            'User-Agent': 'EnergyAnalytics/1.0',
            'Accept': 'application/json',
            'Connection': 'keep-alive'
        }
        
        # Initialize cache
        self.cache = {}
        self.cache_duration = 300  # 5 minutes

    def fetch_realtime_data(self, source: str, max_retries: int = 3) -> Dict[str, Any]:
        """Fetch real-time data with retry mechanism"""
        for attempt in range(max_retries):
            try:
                if self._is_cache_valid(source):
                    logging.info(f"Using cached data for {source}")
                    return self.cache[source]['data']
                
                params = {
                    'api_key': self.api_key,
                    'frequency': 'hourly',
                    'data[0]': 'value',
                    'facets[fueltype][]': source.lower().replace(' ', '-'),
                    'sort[0][column]': 'period',
                    'sort[0][direction]': 'desc',
                    'length': 24
                }
                
                response = self.session.get(
                    EIA_ENDPOINT,
                    params=params,
                    headers=self.eia_headers,
                    timeout=(5, 15)
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if not data.get('response', {}).get('data'):
                        raise ValueError("Empty response data")
                        
                    hourly_data = self._process_hourly_data(source, data, datetime.now().hour)
                    self._update_cache(source, hourly_data)
                    return hourly_data
                    
                elif response.status_code == 500 and attempt < max_retries - 1:
                    logging.warning(f"Server error for {source}, attempt {attempt + 1}")
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                    
                else:
                    logging.error(f"API error {response.status_code} for {source}")
                    return self._get_fallback_hourly_data(source)
                    
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < max_retries - 1:
                    logging.warning(f"Network error for {source}, retrying: {str(e)}")
                    time.sleep(2 ** attempt)
                    continue
                logging.error(f"Network error for {source} after {max_retries} retries")
                return self._get_fallback_hourly_data(source)
                
            except Exception as e:
                logging.error(f"Unexpected error for {source}: {str(e)}")
                return self._get_fallback_hourly_data(source)
                
        return self._get_fallback_hourly_data(source)

    def get_llm_recommendations(self, analysis_text: str) -> str:
        """Get AI recommendations with improved error handling and retries"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Check cache for similar analysis
                cache_key = hash(analysis_text)
                if cache_key in self.cache:
                    cache_data = self.cache[cache_key]
                    if time.time() - cache_data['timestamp'] < self.cache_duration:
                        return cache_data['recommendations']

                payload = {
                    "model": "deepseek-chat",
                    "messages": [{
                        "role": "user",
                        "content": self._create_analysis_prompt(analysis_text)
                    }],
                    "temperature": 0.7,
                    "max_tokens": 1500,
                    "top_p": 0.95,
                    "frequency_penalty": 0.0,
                    "presence_penalty": 0.0
                }

                response = self.session.post(
                    DEEPSEEK_ENDPOINT,
                    headers=self.deepseek_headers,
                    json=payload,
                    timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
                )

                if response.status_code == 200:
                    recommendations = response.json()['choices'][0]['message']['content']
                    # Cache successful response
                    self.cache[cache_key] = {
                        'timestamp': time.time(),
                        'recommendations': recommendations
                    }
                    return recommendations
                elif response.status_code == 401:
                    logging.error("DeepSeek API Authentication failed")
                    return "API Authentication failed. Please check your API key configuration."
                elif response.status_code == 429:
                    if attempt < max_retries - 1:
                        retry_after = int(response.headers.get('Retry-After', retry_delay))
                        time.sleep(retry_after)
                        continue
                    return "Rate limit exceeded. Please try again later."
                else:
                    error_msg = response.json().get('error', {}).get('message', 'Unknown error')
                    logging.error(f"DeepSeek API Error {response.status_code}: {error_msg}")
                    return f"Unable to generate recommendations: {error_msg}"

            except requests.exceptions.Timeout:
                logging.warning(f"Request timeout (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return "Request timed out. Please try again."
                
            except requests.exceptions.ConnectionError:
                logging.error("Network connection error")
                return "Network error occurred. Please check your internet connection."
                
            except Exception as e:
                logging.error(f"Unexpected error in LLM request: {str(e)}")
                return self._get_fallback_recommendations()

        return "Failed to generate recommendations after multiple attempts."

    def _get_fallback_recommendations(self) -> str:
        """Provide fallback recommendations when API fails"""
        return """
        Basic Energy Management Recommendations:
        
        Cost Optimization:
        • Monitor and reduce peak demand usage
        • Schedule operations during off-peak hours
        • Regular maintenance of equipment
        
        Efficiency Improvements:
        • Implement energy monitoring systems
        • Upgrade to energy-efficient equipment
        • Regular system optimization
        
        Environmental Impact:
        • Increase renewable energy usage
        • Implement energy conservation measures
        • Monitor and reduce emissions
        
        Note: These are general recommendations. For more specific advice, 
        please try again when the service is available.
        """

    def _get_fallback_data(self, source: str) -> Dict[str, Any]:
        """Generate fallback data when API fails"""
        current_hour = datetime.now().hour
        source_config = ENERGY_SOURCES.get(source, {'base_prod': 500, 'base_cost': 0.1})
        efficiency = self._calculate_efficiency(source, current_hour)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'production': source_config['base_prod'] * efficiency,
            'efficiency': efficiency,
            'cost': source_config['base_cost'] / (efficiency if efficiency > 0 else 1)
        }

    def _get_fallback_hourly_data(self, source: str) -> Dict[str, Any]:
        """Generate fallback hourly data when API fails"""
        current_hour = datetime.now().hour
        hours = [(current_hour - i) % 24 for i in range(24)]
        
        hourly_production = {}
        hourly_efficiency = {}
        hourly_cost = {}
        
        source_config = ENERGY_SOURCES.get(source, {'base_prod': 500, 'base_cost': 0.1})
        
        for hour in hours:
            efficiency = self._calculate_efficiency(source, hour)
            production = source_config['base_prod'] * efficiency
            cost = source_config['base_cost'] / (efficiency if efficiency > 0 else 1)
            
            hourly_production[hour] = production
            hourly_efficiency[hour] = efficiency
            hourly_cost[hour] = cost
        
        return {
            'timestamp': datetime.now().isoformat(),
            'production': sum(hourly_production.values()) / 24,  # Average production
            'efficiency': sum(hourly_efficiency.values()) / 24,  # Average efficiency
            'cost': sum(hourly_cost.values()) / 24,  # Average cost
            'hourly_production': hourly_production,
            'hourly_efficiency': hourly_efficiency,
            'hourly_cost': hourly_cost
        }

    def _process_hourly_data(self, source: str, data: Dict, current_hour: int) -> Dict[str, Any]:
        """Process API response into hourly format with better validation"""
        hours = [(current_hour - i) % 24 for i in range(24)]
        
        hourly_production = {}
        hourly_efficiency = {}
        hourly_cost = {}
        
        try:
            api_data = data.get('response', {}).get('data', [])
            if not api_data:
                raise ValueError("Empty API response data")
                
            for hour in hours:
                efficiency = self._calculate_efficiency(source, hour)
                # Get the corresponding data point or fallback
                data_point = api_data[hour] if hour < len(api_data) else api_data[-1]
                production = float(data_point.get('value', 0))
                cost = self._calculate_cost(source, efficiency, production)
                
                hourly_production[hour] = production
                hourly_efficiency[hour] = efficiency
                hourly_cost[hour] = cost
            
            return {
                'timestamp': datetime.now().isoformat(),
                'production': sum(hourly_production.values()) / len(hours),
                'efficiency': sum(hourly_efficiency.values()) / len(hours),
                'cost': sum(hourly_cost.values()) / len(hours),
                'hourly_production': hourly_production,
                'hourly_efficiency': hourly_efficiency,
                'hourly_cost': hourly_cost
            }
            
        except Exception as e:
            logging.error(f"Error processing data for {source}: {str(e)}")
            return self._get_fallback_hourly_data(source)

    def _calculate_efficiency(self, source: str, hour: int) -> float:
        """Calculate source-specific efficiency"""
        if source == "Solar":
            return 0.8 * (1 - abs(hour - 12) / 12) if 6 <= hour <= 18 else 0.1
        elif source == "Wind":
            return 0.7 + (hour % 4) * 0.1
        else:
            return 0.85

    def _calculate_cost(self, source: str, efficiency: float, production: float) -> float:
        """Calculate cost based on efficiency and production"""
        base_costs = {
            'Solar': 0.1,
            'Wind': 0.08,
            'Coal': 0.15,
            'Natural Gas': 0.12
        }
        base_cost = base_costs.get(source, 0.1)
        return base_cost / (efficiency if efficiency > 0 else 1)

    def _is_cache_valid(self, source: str) -> bool:
        if source in self.cache:
            age = time.time() - self.cache[source]['timestamp']
            return age < self.cache_duration
        return False

    def _update_cache(self, source: str, data: Dict[str, Any]) -> None:
        self.cache[source] = {
            'timestamp': time.time(),
            'data': data
        }

    def _create_analysis_prompt(self, analysis_text: str) -> str:
        """Create a structured prompt for the LLM"""
        return f"""
        Analyze this energy production data and provide specific recommendations:
        
        {analysis_text}
        
        Please provide detailed recommendations for:
        1. Cost optimization strategies
        2. Energy efficiency improvements
        3. Peak demand management
        4. Environmental impact reduction
        5. Source-specific optimization suggestions
        
        Format your response with clear headings and bullet points.
        Focus on actionable insights based on the current metrics.
        """

    def analyze_hourly_metrics(self) -> str:
        """Generate hourly energy analysis with trends and insights"""
        try:
            current_hour = datetime.now().hour
            hours = [(current_hour - i) % 24 for i in range(24)]
            hours.reverse()  # Show oldest to newest
            
            # Check if we have any data to analyze
            if not any(source in self.cache for source in ENERGY_SOURCES.keys()):
                return "No energy data available for analysis. Please fetch data first."
            
            analysis = []
            total_hourly_production = {h: 0 for h in hours}
            valid_sources = 0
            
            analysis.append("=== Hourly Energy Analysis ===\n")
            
            # Analyze each source
            for source in ENERGY_SOURCES.keys():
                if source in self.cache and self.cache[source].get('data'):
                    data = self.cache[source]['data']
                    hourly_prod = data.get('hourly_production', {})
                    hourly_eff = data.get('hourly_efficiency', {})
                    hourly_cost = data.get('hourly_cost', {})
                    
                    # Validate data
                    if not hourly_prod or not hourly_eff or not hourly_cost:
                        logging.warning(f"Missing hourly data for {source}")
                        continue
                    
                    valid_sources += 1
                    
                    # Calculate metrics with validation
                    valid_prods = [v for v in hourly_prod.values() if isinstance(v, (int, float))]
                    valid_effs = [v for v in hourly_eff.values() if isinstance(v, (int, float))]
                    valid_costs = [v for v in hourly_cost.values() if isinstance(v, (int, float))]
                    
                    if valid_prods and valid_effs and valid_costs:
                        avg_prod = sum(valid_prods) / len(valid_prods)
                        avg_eff = sum(valid_effs) / len(valid_effs)
                        avg_cost = sum(valid_costs) / len(valid_costs)
                        
                        # Find peak and low points with validation
                        peak_prod_hour = max(hours, key=lambda h: hourly_prod.get(h, 0) 
                                           if isinstance(hourly_prod.get(h), (int, float)) else 0)
                        low_prod_hour = min(hours, key=lambda h: hourly_prod.get(h, float('inf')) 
                                          if isinstance(hourly_prod.get(h), (int, float)) else float('inf'))
                        
                        # Add source analysis
                        analysis.append(f"\n{source} Analysis:")
                        analysis.append(f"• Average Production: {avg_prod:.2f} MW")
                        analysis.append(f"• Average Efficiency: {avg_eff*100:.1f}%")
                        analysis.append(f"• Average Cost: €{avg_cost:.2f}/MWh")
                        analysis.append(f"• Peak Production Hour: {peak_prod_hour:02d}:00 ({hourly_prod.get(peak_prod_hour, 0):.2f} MW)")
                        analysis.append(f"• Lowest Production Hour: {low_prod_hour:02d}:00 ({hourly_prod.get(low_prod_hour, 0):.2f} MW)")
                        
                        # Add to total production with validation
                        for hour in hours:
                            prod = hourly_prod.get(hour, 0)
                            if isinstance(prod, (int, float)):
                                total_hourly_production[hour] += prod
            
            if valid_sources == 0:
                return "No valid energy data available for analysis. Please check data sources."
            
            # Overall system analysis with validation
            valid_totals = [v for v in total_hourly_production.values() if v > 0]
            if valid_totals:
                total_avg = sum(valid_totals) / len(valid_totals)
                peak_hour = max(hours, key=lambda h: total_hourly_production[h])
                low_hour = min(hours, key=lambda h: total_hourly_production[h])
                
                analysis.append("\n=== System-wide Metrics ===")
                analysis.append(f"• Average Total Production: {total_avg:.2f} MW")
                analysis.append(f"• Peak Demand Hour: {peak_hour:02d}:00 ({total_hourly_production[peak_hour]:.2f} MW)")
                analysis.append(f"• Lowest Demand Hour: {low_hour:02d}:00 ({total_hourly_production[low_hour]:.2f} MW)")
                analysis.append(f"• Peak/Average Ratio: {(total_hourly_production[peak_hour]/total_avg if total_avg > 0 else 0):.2f}")
            else:
                analysis.append("\n=== System-wide Metrics ===")
                analysis.append("No valid production data available for system-wide analysis.")
            
            return "\n".join(analysis)
            
        except Exception as e:
            logging.error(f"Error generating hourly analysis: {str(e)}")
            return "Failed to generate hourly analysis. Please try again."