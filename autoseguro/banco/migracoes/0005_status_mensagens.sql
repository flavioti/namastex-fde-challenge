-- Status das mensagens (revisão da FDD-0004, seção 5).
-- recebida: mensagem do lead registrada.
-- enviada: resposta do agente registrada.
-- descartada: mensagem do lead recebida depois do encaminhamento ou do encerramento.
ALTER TABLE registro.mensagens ADD COLUMN status text;
UPDATE registro.mensagens SET status = CASE WHEN papel = 'lead' THEN 'recebida' ELSE 'enviada' END;
ALTER TABLE registro.mensagens ALTER COLUMN status SET NOT NULL;
ALTER TABLE registro.mensagens ADD CONSTRAINT mensagens_status_valido
    CHECK (status IN ('recebida', 'enviada', 'descartada'));
