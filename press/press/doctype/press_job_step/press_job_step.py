# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils.safe_exec import safe_exec
import json


class PressJobStep(Document):
	@frappe.whitelist()
	def execute(self):
		if not self.start:
			self.start = frappe.utils.now_datetime()
		self.status = "Running"
		script = frappe.db.get_value(
			"Press Job Type Step",
			{"parent": self.job_type, "step_name": self.step_name},
			"script",
		)
		arguments = json.loads(frappe.db.get_value("Press Job", self.job, "arguments"))
		try:
			local = {"arguments": frappe._dict(arguments), "result": None}
			safe_exec(script, _locals=local)
			result = local["result"]

			if self.wait_until_true:
				self.attempts = self.attempts + 1
				if result:
					self.status = "Success"
				else:
					self.status = "Pending"
					import time

					time.sleep(3)
			else:
				self.status = "Success"
			self.result = str(result)
		except Exception:
			self.status = "Failure"
			self.traceback = frappe.get_traceback(with_context=True)

		self.end = frappe.utils.now_datetime()
		self.duration = self.end - self.start
		self.save()

		job = frappe.get_doc("Press Job", self.job)
		if self.status == "Failure":
			job.fail(local["arguments"])
		else:
			job.next(local["arguments"])
