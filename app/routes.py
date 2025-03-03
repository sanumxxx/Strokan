from flask import Flask, render_template, request, jsonify, session
from scipy import signal
import numpy as np
import json
import plotly
import plotly.graph_objs as go
import os
from scipy import stats


# Инициализация Flask приложения
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['TEMPLATES_AUTO_RELOAD'] = True


# Получаем путь к директории, где находится скрипт
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_FILE = os.path.join(BASE_DIR, 'saved_distributions.json')


# Опционально: инициализация webview для настольного приложения
# import webview
# window = None

class Distribution:
    def __init__(self, dist_type, params):
        self.type = dist_type
        self.params = params

    def get_distribution(self):
        if self.type == 'normal':
            return stats.norm(loc=self.params['mean'], scale=self.params['std'])
        elif self.type == 'exponential':
            return stats.expon(scale=1/self.params['lambda'])

def save_to_file(distributions):
    """Сохраняет параметры распределений в файл"""
    try:
        with open(SAVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(distributions, f, ensure_ascii=False, indent=2)
        print(f"Saved to: {SAVE_FILE}")
        return True
    except Exception as e:
        print(f"Error saving to file: {e}")
        return False


def load_from_file():
    """Загружает параметры распределений из файла"""
    try:
        if os.path.exists(SAVE_FILE):
            print(f"Loading from: {SAVE_FILE}")
            with open(SAVE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            print(f"Save file not found: {SAVE_FILE}")
            default_values = {
                str(i): {
                    "type": "normal",
                    "params": {"mean": 0, "std": 1}
                } for i in range(4)
            }
            save_to_file(default_values)
            return default_values
    except Exception as e:
        print(f"Error loading from file: {e}")
        return {
            str(i): {
                "type": "normal",
                "params": {"mean": 0, "std": 1}
            } for i in range(4)
        }


@app.route('/')
def index():
    try:
        saved_distributions = load_from_file()
        session['distributions'] = json.dumps(saved_distributions)
        return render_template('index.html', saved_distributions=saved_distributions)
    except Exception as e:
        print(f"Error in index route: {e}")
        default_values = {
            str(i): {
                "type": "normal",
                "params": {"mean": 0, "std": 1}
            } for i in range(4)
        }
        return render_template('index.html', saved_distributions=default_values)


@app.route('/save_parameters', methods=['POST'])
def save_parameters():
    try:
        data = request.json
        print("Received data:", data)
        session['distributions'] = json.dumps(data)
        if save_to_file(data):
            print("Parameters saved successfully")
            return jsonify({'status': 'success'})
        else:
            print("Failed to save parameters")
            return jsonify({
                'status': 'error',
                'message': 'Failed to save parameters to file'
            }), 500
    except Exception as e:
        print("Error in save_parameters:", str(e))
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400


@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.json
        print("Calculation request:", data)

        if 'distributions' not in session:
            return jsonify({'status': 'error', 'message': 'No distributions saved'}), 400

        distributions = json.loads(session['distributions'])
        print("Loaded distributions:", distributions)

        selected_dists = []
        for val in data['combination']:
            # Проверка наличия индекса в словаре
            if str(val) not in distributions:
                return jsonify({
                    'status': 'error',
                    'message': f'Распределение с индексом {val} не найдено'
                }), 400

            dist_data = distributions[str(val)]
            selected_dists.append(Distribution(dist_data['type'], dist_data['params']))

        # Вычисляем свертку на всем диапазоне
        result_full, x_full = calculate_convolution_x(selected_dists)

        if data['calc_type'] == 'x':
            x_min = float(data['x_min'])
            x_max = float(data['x_max'])

            # Проверка на корректность диапазона
            if x_min >= x_max:
                return jsonify({
                    'status': 'error',
                    'message': 'Левая граница должна быть меньше правой'
                }), 400

            # Находим индексы для обрезки
            mask = (x_full >= x_min) & (x_full <= x_max)
            x_plot = x_full[mask]
            y_plot = result_full[mask]

            # Проверка на пустой диапазон
            if len(x_plot) == 0:
                return jsonify({
                    'status': 'error',
                    'message': 'Указанный диапазон находится вне области определения распределения'
                }), 400

            # Вычисляем вероятность в заданном диапазоне
            dx = x_full[1] - x_full[0]
            probability = np.sum(result_full[mask]) * dx

            # Создаем график
            fig = go.Figure()
            # Добавляем полное распределение как фон
            fig.add_trace(go.Scatter(
                x=x_full.tolist(),
                y=result_full.tolist(),
                mode='lines',
                line=dict(color='lightgrey'),
                name='Полное распределение'
            ))
            # Добавляем выделенную область
            fig.add_trace(go.Scatter(
                x=x_plot.tolist(),
                y=y_plot.tolist(),
                mode='lines',
                fill='tozeroy',
                fillcolor='rgba(0,176,246,0.2)',
                line=dict(color='blue'),
                name=f'P({x_min} ≤ X ≤ {x_max}) = {probability:.4f}'
            ))
            fig.update_layout(
                title=f'P({x_min} ≤ X ≤ {x_max}) = {probability:.4f}',
                xaxis_title='X',
                yaxis_title='Плотность вероятности',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )

            plot_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

            return jsonify({
                'status': 'success',
                'plot': plot_json,
                'probability': probability
            })

        else:  # calc_type == 'y'
            y_target = float(data['y'])
            if not 0 <= y_target <= 1:
                return jsonify({
                    'status': 'error',
                    'message': 'Значение вероятности должно быть от 0 до 1'
                }), 400

            x_min = find_x_for_probability(result_full, x_full, y_target)

            if x_min is None:
                return jsonify({
                    'status': 'error',
                    'message': 'Не удалось найти подходящее значение X'
                }), 400

            # Создаем график для визуализации
            # Показываем распределение от -inf до x_min
            mask = x_full <= x_min
            fig = go.Figure()
            # Полное распределение
            fig.add_trace(go.Scatter(
                x=x_full.tolist(),
                y=result_full.tolist(),
                mode='lines',
                line=dict(color='lightgrey'),
                name='Полное распределение'
            ))
            # Выделенная область
            fig.add_trace(go.Scatter(
                x=x_full[mask].tolist(),
                y=result_full[mask].tolist(),
                mode='lines',
                fill='tozeroy',
                fillcolor='rgba(0,176,246,0.2)',
                line=dict(color='blue'),
                name=f'P(X ≤ {x_min:.4f}) = {y_target}'
            ))
            fig.add_vline(
                x=x_min,
                line_dash="dash",
                line_color="red",
                annotation_text=f"X = {x_min:.4f}"
            )
            fig.update_layout(
                title=f'P(X ≤ {x_min:.4f}) = {y_target}',
                xaxis_title='X',
                yaxis_title='Плотность вероятности',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )

            plot_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

            return jsonify({
                'status': 'success',
                'x_min': float(x_min),
                'plot': plot_json
            })

    except Exception as e:
        print("Error in calculate:", str(e))
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400


def calculate_convolution_x(distributions):
    try:
        if len(distributions) == 0:
            raise ValueError("No distributions provided")

        # Используем широкий диапазон для вычислений
        x_dense = np.linspace(-20, 20, 4000)
        dx = x_dense[1] - x_dense[0]

        # Получаем PDF для каждого распределения
        pdfs = []
        for dist in distributions:
            dist_obj = dist.get_distribution()
            pdf = dist_obj.pdf(x_dense)
            # Нормализуем PDF
            pdf = pdf / (np.sum(pdf) * dx)
            pdfs.append(pdf)

        print("PDF values:", [np.max(pdf) for pdf in pdfs])

        # Выполняем свертку последовательно
        result = pdfs[0]
        for i in range(1, len(pdfs)):
            conv = signal.fftconvolve(result, pdfs[i], mode='same') * dx
            result = conv

        # Нормализуем результат
        result = result / (np.sum(result) * dx)

        print("Max result value:", np.max(result))
        return result, x_dense

    except Exception as e:
        print("Error in convolution calculation:", str(e))
        raise


def find_x_for_probability(result_full, x_full, target_prob):
    """
    Находит значение x, для которого P(X ≤ x) = target_prob
    """
    try:
        dx = x_full[1] - x_full[0]
        # Вычисляем интегральную функцию распределения
        cdf = np.cumsum(result_full) * dx
        # Нормализуем
        cdf = cdf / cdf[-1]

        # Находим индекс, где CDF наиболее близка к целевой вероятности
        idx = np.argmin(np.abs(cdf - target_prob))
        return x_full[idx]

    except Exception as e:
        print("Error in finding x for probability:", str(e))
        return None


if __name__ == "__main__":
    # Если приложение запускается как основной скрипт (не через webview)
    app.run(debug=True, host='0.0.0.0')

# Для запуска в режиме desktop-приложения
# def start_server():
#     app.run()
#
# def create_window():
#     global window
#     window = webview.create_window('Калькулятор распределений', app)
#     webview.start(start_server)