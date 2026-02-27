jo.framework:loadFile("client")
jo.framework:loadFile("_custom", "client")

local myIdentifiers = {}
--- A function to get the user identifiers
function jo.framework:getMyIdentifiers()
  if table.isEmpty(myIdentifiers) then
    myIdentifiers = jo.callback.triggerServer(jo.resourceName .. ":server:framework:getPlayerIdentifiers")
  end
  return myIdentifiers
end
