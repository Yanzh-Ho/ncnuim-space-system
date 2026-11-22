from fastapi import Request, HTTPException


def currentUser(request: Request):
	"""拿目前登入的人，沒登入回傳 None（不擋人，給公開頁面用）"""
	return request.session.get("user")


def chkLogin(*roles):
	"""
	守門員：
	chkLogin()                    → 有登入就放行
	chkLogin("admin")             → 只放管理員
	chkLogin("teacher", "admin")  → 老師或管理員
	"""
	def checker(request: Request):
		loginUser = request.session.get("user")
		if loginUser is None:
			raise HTTPException(status_code=401, detail="請先登入")
		if roles and loginUser["role"] not in roles:
			raise HTTPException(status_code=403, detail="沒有權限")
		return loginUser
	return checker
