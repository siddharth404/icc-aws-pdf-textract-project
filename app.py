#!/usr/bin/env python3
from cdk.receipt_processor import ReceiptProcessorWorkflow
import aws_cdk as cdk

app = cdk.App()
ReceiptProcessorWorkflow(app, "ReceiptProcessorWorkflow")
app.synth()
