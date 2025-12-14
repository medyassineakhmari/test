
# run in WSL or Linux,

activate-local-venv:
	# the .venv should be inside the spark ml folder, not in the root folder
	# this venv is to be used to train spark ml model inside the spark ml folder
	python3 -m venv .venv
	source .venv/bin/activate


install-dependencies:
	pip install pandas
	# to run jupyter notebooks with pycharm (optional)
	#pip install jupyter jupyterlab ipykernel
	# install pyspark
	pip install pyspark numpy

# install JDK 17 if not have it
install-jdk-in-wsl:
	sudo apt-get update
	sudo apt-get install openjdk-17-jdk -y


train-and-save-pipeline-model:
	python3 train_and_save_model_binary.py
	#python3 train_and_save_model_multiclass.py

set-for-wsl:
	unset SPARK_HOME
	# set JAVA_HOME for WSL
	echo "export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64" >> ~/.bashrc
	echo "export PATH=\$JAVA_HOME/bin:\$PATH" >> ~/.bashrc
	source ~/.bashrc


create_test-data:
	python3 produce_test_data.py

# test the created model on test data
run_inferece:
	python3 inference_binary.py
	#python3 inference_multi.py