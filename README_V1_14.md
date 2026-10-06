# AIAffiliateIntelligence v1.14

## Prévia de vídeo recolhível
- A prévia do vídeo inicia recolhida para economizar espaço vertical.
- Cabeçalho “Prévia do vídeo” ganhou ação Expandir/Recolher com seta no canto direito.
- O player só é renderizado quando a seção está expandida.
- Mantidos controles nativos de reprodução, tela cheia, volume e progresso.
- Mantidas as correções da v1.13.6 e anteriores.

## Próxima evolução da linha 1.14
A arquitetura de imagens reais do produto (até 3 referências oficiais) deve ser implementada sem depender de recriação textual da embalagem pela IA.

## V1.14 Agência — referências visuais reais
- Até 3 fotos reais por campanha, com principal, origem, hash SHA-256, dimensões e auditoria.
- Upload JPG/PNG/WebP, validação de conteúdo, mínimo 300 px, proporção segura e limite 12 MB.
- Importação da imagem oficial já cadastrada no produto com proteção SSRF e sem seguir redirects.
- Cópia das referências para R2; a geração usa URLs temporárias assinadas, não depende da URL externa.
- Geração fal.ai passa automaticamente para Kling V3 Image-to-Video quando existem referências.
- Produto enviado como elemento visual e prompt defensivo contra troca de embalagem, logo, variante e rótulo.
- Geração de vídeo comercial bloqueada sem ao menos uma referência real; 3 são recomendadas.
- Prévia do vídeo permanece recolhida por padrão e expansível.
