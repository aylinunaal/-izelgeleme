from Ui_mainForm import Ui_MainWindow
from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSignal, QObject
import sys
import numpy as np
import matplotlib.pyplot as plt

class Communicate(QObject):
    data_signal = pyqtSignal(list)

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        self.iterations = 0
        self.temperature = 0
        self.comboBox.currentIndexChanged.connect(self.toggle_layer)
        self.stackedWidget.setCurrentIndex(0)
        self.hesapla.clicked.connect(self.sa_calistir)
        self.is_sayisi.setMinimum(1)
        self.makine_sayisi.setMinimum(1)
        self.olustur.clicked.connect(self.openNewForm)

    def toggle_layer(self):
        self.stackedWidget.setCurrentIndex(self.comboBox.currentIndex())

    def sa_calistir(self):
        optimization_method = ''
        if self.stackedWidget.currentIndex() == 0:
            optimization_method = 'End Temperature'
            self.temp = int(self.bitis_sicakligi.text())
        elif self.stackedWidget.currentIndex() == 1 and self.iterasyon_sayisi.text():
            optimization_method = 'Number of Iterations'
            self.iterations = int(self.iterasyon_sayisi.text())

        num_jobs = int(self.is_sayisi.text())
        num_machines = int(self.makine_sayisi.text())
        initial_temp = int(self.baslangic_sicakligi.text())
        alpha = float(self.alfa.text().replace(',', '.'))  # Handle locale-specific decimal separator

        order, time, job_times = self.sa_algorithm(self.job_machine_times, num_jobs, num_machines, initial_temp, alpha, optimization_method)

        order_str = ' -> '.join([f'İş {job+1}' for job in order])
        self.result_2.setText(order_str)
        self.result.setText(str(time))
        
        self.plot_gantt_chart(order, job_times, num_machines)

    def openNewForm(self):
        num_jobs = self.is_sayisi.value()
        num_machines = self.makine_sayisi.value()
        self.newForm = JobMachineForm(num_jobs, num_machines)
        self.newForm.communicate.data_signal.connect(self.handleData)
        self.newForm.exec_()

    def handleData(self, job_machine_times):
        self.job_machine_times = job_machine_times
        self.updateTable(job_machine_times)

    def sa_algorithm(self, job_machine_times, num_jobs, num_machines, initial_temp, alpha, optimization_method):
        def get_total_time(order, times):
            machine_times = np.zeros(num_machines)
            job_finish_times = np.zeros(num_jobs)
            job_start_times = np.zeros((num_jobs, num_machines))

            for job in order:
                for machine in range(num_machines):
                    start_time = max(machine_times[machine], job_finish_times[job])
                    duration = times[job][machine]
                    finish_time = start_time + duration
                    machine_times[machine] = finish_time
                    job_finish_times[job] = finish_time
                    job_start_times[job][machine] = start_time

            return machine_times.max(), job_start_times

        def acceptance_probability(current_time, new_time, temperature):
            if new_time < current_time:
                return 1.0
            return np.exp((current_time - new_time) / temperature)

        current_order = list(range(num_jobs))
        np.random.shuffle(current_order)
        current_time, job_times = get_total_time(current_order, job_machine_times)

        best_order = current_order.copy()
        best_time = current_time
        best_job_times = job_times.copy()
        temperature = initial_temp

        if optimization_method == 'End Temperature':
            while temperature > self.temp:
                new_order = current_order.copy()
                idx1, idx2 = np.random.choice(num_jobs, size=2, replace=False)
                new_order[idx1], new_order[idx2] = new_order[idx2], new_order[idx1]
                new_time, job_times = get_total_time(new_order, job_machine_times)

                if acceptance_probability(current_time, new_time, temperature) > np.random.rand():
                    current_order = new_order
                    current_time = new_time

                if new_time < best_time:
                    best_order = new_order
                    best_time = new_time
                    best_job_times = job_times.copy()
                temperature *= alpha

        elif optimization_method == 'Number of Iterations':
            for _ in range(self.iterations):
                new_order = current_order.copy()
                idx1, idx2 = np.random.choice(num_jobs, size=2, replace=False)
                new_order[idx1], new_order[idx2] = new_order[idx2], new_order[idx1]
                new_time, job_times = get_total_time(new_order, job_machine_times)

                if acceptance_probability(current_time, new_time, temperature) > np.random.rand():
                    current_order = new_order
                    current_time = new_time

                if new_time < best_time:
                    best_order = new_order
                    best_time = new_time
                    best_job_times = job_times.copy()

                temperature *= alpha

        return best_order, best_time, best_job_times

    def plot_gantt_chart(self, order, job_start_times, num_machines):
        fig, ax = plt.subplots(figsize=(12, 8))  # Şemanın boyutunu arttır
        colors = plt.cm.tab20(np.linspace(0, 1, len(order)))

        for i, job in enumerate(order):
            for machine in range(num_machines):
                start_time = job_start_times[job][machine]
                duration = self.job_machine_times[job][machine]
                ax.barh(machine, duration, left=start_time, color=colors[i], edgecolor='black', label=f'İş {job+1}' if i == 0 else "")
                ax.text(start_time + duration / 2, machine, f'İş {job+1}', ha='center', va='center', color='white')

        ax.set_xlabel('Zaman')
        ax.set_ylabel('Makine')
        ax.set_yticks(range(num_machines))
        ax.set_yticklabels([f'Makine {i+1}' for i in range(num_machines)])
        ax.set_title('Gantt Şeması')
       
        ax.set_xlim(0, ax.get_xlim()[1] + 1)  # 1 birim artır

        # X ekseninde tam sayıları göster
        max_time = int(ax.get_xlim()[1] + 1)  # x eksenindeki en büyük değeri al
        ax.set_xticks(np.arange(0, max_time, 1))
        ax.set_xticklabels([str(i) for i in range(max_time)], rotation=45)  # X eksenindeki sayıları 45 derece döndür

        plt.show()

    def updateTable(self, job_machine_times):
        num_jobs = len(job_machine_times)
        num_machines = len(job_machine_times[0]) if num_jobs > 0 else 0

        self.table.setRowCount(num_jobs)
        self.table.setColumnCount(num_machines)

        headers = [f'Makine {i+1}' for i in range(num_machines)]
        self.table.setHorizontalHeaderLabels(headers)

        for job in range(num_jobs):
            for machine in range(num_machines):
                self.table.setItem(job, machine, QTableWidgetItem(str(job_machine_times[job][machine])))

class JobMachineForm(QDialog):
    communicate = Communicate()
    def __init__(self, num_jobs, num_machines):
        super().__init__()
        self.num_jobs = num_jobs
        self.num_machines = num_machines
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Enter Machine Times')
        self.layout = QVBoxLayout()

        self.fieldsLayout = QGridLayout()
        self.job_machine_inputs = []

        for machine in range(self.num_machines):
            machine_label = QLabel(f'Makine {machine + 1}')
            self.fieldsLayout.addWidget(machine_label, 0, machine + 1)

        for job in range(self.num_jobs):
            job_label = QLabel(f'İş {job + 1}')
            self.fieldsLayout.addWidget(job_label, job + 1, 0)
            job_machine_times = []
            for machine in range(self.num_machines):
                machine_input = QLineEdit()
                self.fieldsLayout.addWidget(machine_input, job + 1, machine + 1)
                job_machine_times.append(machine_input)
            self.job_machine_inputs.append(job_machine_times)

        self.layout.addLayout(self.fieldsLayout)

        self.submitButton = QPushButton('Onayla')
        self.submitButton.clicked.connect(self.submit)
        self.layout.addWidget(self.submitButton)

        self.setLayout(self.layout)

    def submit(self):
        job_machine_times = []
        for job in range(self.num_jobs):
            machine_times = []
            for machine in range(self.num_machines):
                time_value = self.job_machine_inputs[job][machine].text()
                if time_value.isdigit():
                    machine_times.append(int(time_value))
                else:
                    machine_times.append(0)
            job_machine_times.append(machine_times)

        self.communicate.data_signal.emit(job_machine_times)
        self.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainForm = MainWindow()
    mainForm.show()

    sys.exit(app.exec_())

