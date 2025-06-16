# Diretório com os manifests Terraform
TF_DIR := infra/v1

# Diretórios/locais para build
BUILD_DIR := build
LAMBDA_SRC := lambda
LAYER_SRC  := lambda-layer/opt

# Caminhos dos pacotes gerados
LAMBDA_ZIP := $(BUILD_DIR)/deployment-package.zip
LAYER_ZIP  := $(BUILD_DIR)/ffmpeg-layer.zip

.PHONY: all build-lambda build-layer terraform-init terraform-plan terraform-apply clean

# Alvo padrão: gera ambos os pacotes
all: build-lambda build-layer

# Empacota o código Python da Lambda
build-lambda:
	@echo "➡️  Gerando pacote da Lambda..."
	mkdir -p $(BUILD_DIR)
	cd $(LAMBDA_SRC) && zip -r ../$(LAMBDA_ZIP) .
	@echo "✔ Pacote gerado em $(LAMBDA_ZIP)"

# Empacota o layer (FFmpeg) na estrutura /opt
build-layer:
	@echo "➡️  Gerando pacote do FFmpeg Layer..."
	mkdir -p $(BUILD_DIR)
	cd lambda-layer && zip -r ../$(LAYER_ZIP) opt
	@echo "✔ Layer gerado em $(LAYER_ZIP)"

# Inicializa o Terraform
terraform-init:
	@echo "➡️  Terraform Init em $(TF_DIR)..."
	cd $(TF_DIR) && terraform init

# Gera e mostra o plano do Terraform
terraform-plan: build-lambda build-layer terraform-init
	@echo "➡️  Terraform Plan em $(TF_DIR)..."
	cd $(TF_DIR) && terraform plan

# Aplica o Terraform (deploy)
terraform-apply:
	@echo "➡️  Terraform Apply em $(TF_DIR)..."
	cd $(TF_DIR) && terraform apply

# Limpa ZIPs gerados
clean:
	@echo "➡️  Limpando artefatos de build..."
	rm -rf $(BUILD_DIR)/*.zip
	@echo "✔ Limpeza completa"


# Destrói a infraestrutura provisionada pelo Terraform
terraform-destroy:
	@echo "➡️  Terraform Destroy em $(TF_DIR)..."
	cd $(TF_DIR) && terraform destroy -auto-approve
