provider "aws" {
  region  = "eu-west-1"
  profile = "${var.aws_profile}"
}

terraform {
  backend "s3" {
    profile = "gsg-intools-prod"
    bucket  = "gsg-intls-crisisapp"
    key     = "crisisapp/terraform.tfstate"
    region  = "eu-west-1"
  }
}
