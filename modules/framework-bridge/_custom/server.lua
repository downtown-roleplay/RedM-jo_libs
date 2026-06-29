-------------
-- Server Side: Add Event listeners for the script
-- ⚠️ This file is executed in all resources that load the framework module ⚠️
-------------

-- Handler para onCharacterSelected (fallback seguro)
-- O core/ bridge já tem isso, mas este fallback garante compatibilidade
-- mesmo se o _custom for usado como fallback
if not jo.framework.onCharacterSelected then
  function jo.framework:onCharacterSelected(cb)
    AddEventHandler("characterLoaded", function(characterData)
      if characterData and characterData.playerId then
        cb(characterData.playerId)
      end
    end)
  end
end
