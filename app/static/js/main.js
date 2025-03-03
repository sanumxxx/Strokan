// Обработка изменения типа распределения
document.querySelectorAll('select[name^="type-"]').forEach(select => {
    select.addEventListener('change', function() {
        const index = this.name.split('-')[1];
        const normalParams = document.querySelector(`.normal-params-${index}`);
        const exponentialParams = document.querySelector(`.exponential-params-${index}`);

        if (this.value === 'normal') {
            normalParams.style.display = 'block';
            exponentialParams.style.display = 'none';
        } else {
            normalParams.style.display = 'none';
            exponentialParams.style.display = 'block';
        }
    });
});

// Обработка формы параметров
document.getElementById('parameters-form').addEventListener('submit', async function(e) {
    e.preventDefault();

    const data = {};
    for (let i = 0; i < 4; i++) {
        const type = document.querySelector(`select[name="type-${i}"]`).value;
        const params = {};

        if (type === 'normal') {
            params.mean = parseFloat(document.querySelector(`input[name="mean-${i}"]`).value);
            params.std = parseFloat(document.querySelector(`input[name="std-${i}"]`).value);
        } else {
            params.lambda = parseFloat(document.querySelector(`input[name="lambda-${i}"]`).value);
        }

        data[i] = {type, params};
    }

    try {
        const response = await fetch('/save_parameters', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            alert('Параметры сохранены');
        } else {
            alert('Ошибка при сохранении параметров');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Ошибка при отправке данных');
    }
});

// Обработка изменения типа расчета
document.getElementById('calc-type').addEventListener('change', function() {
    const xInputs = document.getElementById('x-inputs');
    const yInput = document.getElementById('y-input');

    if (this.value === 'x') {
        xInputs.style.display = 'block';
        yInput.style.display = 'none';
    } else {
        xInputs.style.display = 'none';
        yInput.style.display = 'block';
    }
});

// Обработка формы расчетов
document.getElementById('calculations-form').addEventListener('submit', async function(e) {
    e.preventDefault();

    const combination = document.getElementById('combination').value
        .split(' ')
        .map(Number);

    const calcType = document.getElementById('calc-type').value;
    const data = {
        combination,
        calc_type: calcType
    };

    if (calcType === 'x') {
        data.x_min = parseFloat(document.getElementById('x-min').value);
        data.x_max = parseFloat(document.getElementById('x-max').value);
    } else {
        data.y = parseFloat(document.getElementById('y-value').value);
    }

    try {
        const response = await fetch('/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.status === 'error') {
            alert(result.message || 'Произошла ошибка при расчетах');
            return;
        }

        if (calcType === 'x') {
            const plotData = JSON.parse(result.plot);
            console.log('Plot data:', plotData); // Для отладки
            Plotly.newPlot('plot', plotData.data, plotData.layout);
        } else {
            const resultDiv = document.getElementById('result');
            if (result.x_min === null || result.x_max === null) {
                resultDiv.innerHTML = '<div class="alert alert-warning">Не удалось найти подходящий диапазон X</div>';
            } else {
                resultDiv.innerHTML = `
                    <div class="alert alert-info">
                        Диапазон X: от ${result.x_min.toFixed(4)} до ${result.x_max.toFixed(4)}
                    </div>
                `;
            }
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Ошибка при выполнении расчетов');
    }
});