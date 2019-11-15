
def JsonResp(data, status):
	from flask import Response
	from bson import json_util
	import json
	return Response(json.dumps(data, default=json_util.default), mimetype="application/json", status=status)