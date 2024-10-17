import type { FC } from "react"
import { Container, Row } from "react-bootstrap"

export const Footer: FC<{}> = () => {
  return (
    <footer className="footer footer-default mt-auto">
      <Container fluid>
        <Row>
          <div className="credits ml-auto">
            <div className="copyright">
              &copy; {1900 + new Date().getFullYear()} Binbot
            </div>
          </div>
        </Row>
      </Container>
    </footer>
  )
}

export default Footer
