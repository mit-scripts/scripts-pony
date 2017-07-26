package main

import (
	"bufio"
	"crypto/x509"
	"encoding/pem"
	"errors"
	"flag"
	"fmt"
	"io/ioutil"
	"os"
)

func verifyCerts(certs []byte, hostname string) error {

	// Parse the certificates
	inputCertificates := []*x509.Certificate{}
	rest := certs
	var block *pem.Block
	for {
		block, rest = pem.Decode(rest)
		if block == nil {
			if len(rest) == 0 {
				break
			} else {
				return fmt.Errorf("extraneous data included: %s", rest)
			}
		}
		if block.Type != "CERTIFICATE" {
			return errors.New("certificate chain should only contain certificates")
		}
		cert, err := x509.ParseCertificate(block.Bytes)
		if err != nil {
			return err
		}
		inputCertificates = append(inputCertificates, cert)
	}

	// prepare a call to Verify()
	finalCert := inputCertificates[0]
	restOfCerts := inputCertificates[1:]

	pool := x509.NewCertPool()
	for _, cert := range restOfCerts {
		pool.AddCert(cert)
	}

	opts := x509.VerifyOptions{
		DNSName:       hostname,
		Intermediates: pool,
	}

	chains, err := finalCert.Verify(opts)
	if err != nil {
		return err
	}

	// check that the output matches the chain the user presented.
	if len(chains) == 0 {
		return errors.New("chain invalid or missing a component")
	}
	var correctChain bool
	for _, chain := range chains {
		// fmt.Printf("checking chain #%d\n", idx)
		// check if this chain is in the order presented by the user
		correctChain = true
		for idx2, cert := range chain[:len(chain)-1] {
			if idx2 >= len(inputCertificates) {
				// fmt.Println("  too many")
				correctChain = false
				break
			}
			correctCert := cert.Equal(inputCertificates[idx2])
			// fmt.Printf("  cert #%d: %t\n", idx2, correctCert)
			correctChain = correctChain && correctCert
		}
		if correctChain {
			return nil
		}
	}
	return errors.New("certificate chain as presented is out of order")
}

func main() {
	reader := bufio.NewReader(os.Stdin)
	hostnamePtr := flag.String("hostname", "google.com", "Hostname to verify these certificates against, e.g. yoursite.com")
	flag.Parse()
	certificateBytes, err := ioutil.ReadAll(reader)
	if err != nil {
		fmt.Fprintln(os.Stderr, "Failed to read certificates from stdin")
		os.Exit(2)
	}
	err = verifyCerts(certificateBytes, *hostnamePtr)
	if err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
		os.Exit(1)
	}
	fmt.Printf("successfully verified certificates for host: %s\n", *hostnamePtr)
}

