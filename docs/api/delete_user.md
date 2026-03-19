# 用户删除接口文档

## 接口信息

**路径**: `DELETE /api/v1/users/{user_id}`

**权限**: 需要管理员权限

## 响应场景

### 1. 删除成功 (200 OK)

```json
{
    "success": true,
    "message": "用户删除成功",
    "user_id": 5,
    "username": "testuser",
    "detail": "用户已被成功删除，所有关联数据已清理"
}
```

### 2. 删除失败 - 不能删除自己的账户 (400 Bad Request)

```json
{
    "success": false,
    "message": "用户删除失败",
    "error_code": "CANNOT_DELETE_SELF",
    "detail": "不能删除自己的账户"
}
```

### 3. 删除失败 - 无权限 (403 Forbidden)

当非管理员用户尝试删除时：

```json
{
    "success": false,
    "message": "用户删除失败",
    "error_code": "FORBIDDEN",
    "detail": "需要管理员权限"
}
```

### 4. 删除失败 - 用户不存在 (404 Not Found)

```json
{
    "success": false,
    "message": "用户删除失败",
    "error_code": "USER_NOT_FOUND",
    "detail": "用户ID 999 不存在"
}
```

### 5. 删除失败 - 用户有关联数据 (409 Conflict)

当用户是项目所有者时：

```json
{
    "success": false,
    "message": "用户删除失败",
    "error_code": "HAS_DEPENDENCIES",
    "detail": "用户是 3 个项目的所有者，请先转移项目所有权"
}
```

### 6. 删除失败 - 超级管理员保护 (423 Locked)

尝试删除超级管理员时：

```json
{
    "success": false,
    "message": "用户删除失败",
    "error_code": "SUPERUSER_PROTECTED",
    "detail": "无法删除超级管理员账户"
}
```

### 7. 删除失败 - 服务器内部错误 (500 Internal Server Error)

```json
{
    "success": false,
    "message": "用户删除失败",
    "error_code": "INTERNAL_ERROR",
    "detail": "删除用户时发生内部错误，请稍后重试"
}
```

## 业务逻辑流程

1. **权限检查**: 验证当前用户是否为管理员
2. **自我删除检查**: 验证是否删除自己的账户
3. **用户存在性检查**: 验证被删除用户是否存在
4. **超级管理员保护**: 验证被删除用户不是超级管理员
5. **关联数据检查**: 
   - 检查用户是否为项目所有者
   - 检查用户创建的测试用例、测试计划等
   - 记录执行记录等关联信息
6. **执行删除**: 删除用户及关联数据
7. **返回结果**: 返回删除结果

## 错误码说明

| 错误码 | HTTP状态码 | 说明 |
|--------|-----------|------|
| CANNOT_DELETE_SELF | 400 | 不能删除自己的账户 |
| FORBIDDEN | 403 | 无权限，需要管理员权限 |
| USER_NOT_FOUND | 404 | 用户不存在 |
| HAS_DEPENDENCIES | 409 | 用户有关联数据，无法删除 |
| SUPERUSER_PROTECTED | 423 | 超级管理员账户受保护 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |
| BUSINESS_ERROR | 400 | 其他业务错误 |

## 使用示例

### cURL 示例

```bash
# 删除用户
curl -X DELETE "http://localhost:5000/api/v1/users/5" \
  -H "Authorization: Bearer {token}"
```

### Python 示例

```python
import httpx

async def delete_user(user_id: int, token: str):
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"http://localhost:5000/api/v1/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"删除成功: {result['username']}")
        else:
            error = response.json()
            print(f"删除失败: {error['detail']}")
```

### JavaScript 示例

```javascript
async function deleteUser(userId, token) {
  const response = await fetch(`http://localhost:5000/api/v1/users/${userId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  const data = await response.json();
  
  if (response.ok) {
    console.log(`删除成功: ${data.username}`);
  } else {
    console.error(`删除失败: ${data.detail}`);
  }
}
```
